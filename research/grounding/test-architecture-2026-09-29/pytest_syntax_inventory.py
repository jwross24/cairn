import argparse
import ast
import gzip
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath

DEFAULT_SOURCE_SHA = "da48ef2c9796aa5ea72bb3e9aa870c7dfb2eed31"
ROOT = Path(__file__).resolve().parents[3]
GIT = shutil.which("git")


def git_bytes(*args):
    if GIT is None:
        raise RuntimeError("git executable is unavailable")
    return subprocess.run(
        [GIT, *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def pytest_bindings(tree):
    modules = set()
    marks = set()
    params = set()
    raises = set()
    fixtures = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest":
                    modules.add(alias.asname or "pytest")
        elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
            for alias in node.names:
                local = alias.asname or alias.name
                if alias.name == "mark":
                    marks.add(local)
                elif alias.name == "param":
                    params.add(local)
                elif alias.name == "raises":
                    raises.add(local)
                elif alias.name == "fixture":
                    fixtures.add(local)
    return modules, marks, params, raises, fixtures


def is_pytest_attribute(node, modules, name):
    return (
        isinstance(node, ast.Attribute)
        and node.attr == name
        and isinstance(node.value, ast.Name)
        and node.value.id in modules
    )


def yield_count(function):
    pending = list(function.body)
    count = 0
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            count += 1
        pending.extend(ast.iter_child_nodes(node))
    return count


def analyze_source(path, source):
    tree = ast.parse(source, filename=path)
    modules, marks, params, raises, fixtures = pytest_bindings(tree)
    rows = {
        "asyncio_decorators": [],
        "async_test_defs": [],
        "pytest_param": [],
        "pytest_raises": [],
        "autouse_fixtures": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
            rows["async_test_defs"].append({"line": node.lineno, "name": node.name})

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(decorator, ast.Call) else decorator
                mark_target = (
                    isinstance(target, ast.Attribute)
                    and target.attr == "asyncio"
                    and (
                        is_pytest_attribute(target.value, modules, "mark")
                        or (isinstance(target.value, ast.Name) and target.value.id in marks)
                    )
                )
                if mark_target:
                    rows["asyncio_decorators"].append({"line": node.lineno, "name": node.name})

                fixture_target = decorator.func if isinstance(decorator, ast.Call) else decorator
                is_fixture = is_pytest_attribute(fixture_target, modules, "fixture") or (
                    isinstance(fixture_target, ast.Name) and fixture_target.id in fixtures
                )
                if is_fixture and isinstance(decorator, ast.Call):
                    autouse = next(
                        (keyword.value for keyword in decorator.keywords if keyword.arg == "autouse"),
                        None,
                    )
                    if isinstance(autouse, ast.Constant) and autouse.value is True:
                        rows["autouse_fixtures"].append(
                            {
                                "line": node.lineno,
                                "name": node.name,
                                "yield_count": yield_count(node),
                            }
                        )

        if not isinstance(node, ast.Call):
            continue

        if is_pytest_attribute(node.func, modules, "param") or (
            isinstance(node.func, ast.Name) and node.func.id in params
        ):
            id_value = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "id"),
                None,
            )
            rows["pytest_param"].append(
                {
                    "line": node.lineno,
                    "has_literal_id_keyword": id_value is not None,
                    "id_source": ast.unparse(id_value) if id_value is not None else None,
                    "literal_id": (
                        id_value.value
                        if isinstance(id_value, ast.Constant) and isinstance(id_value.value, str)
                        else None
                    ),
                }
            )

        if is_pytest_attribute(node.func, modules, "raises") or (
            isinstance(node.func, ast.Name) and node.func.id in raises
        ):
            rows["pytest_raises"].append(
                {
                    "line": node.lineno,
                    "has_literal_match_keyword": any(keyword.arg == "match" for keyword in node.keywords),
                    "has_keyword_expansion": any(keyword.arg is None for keyword in node.keywords),
                }
            )

    return rows


def inventory(source_sha):
    tree_paths = [
        path
        for path in git_bytes("ls-tree", "-r", "--name-only", "-z", source_sha, "--", "tests").decode().split("\0")
        if path
    ]
    excluded_var_paths = [path for path in tree_paths if "var" in PurePosixPath(path).parts]
    test_paths = [path for path in tree_paths if path not in excluded_var_paths]
    suffix_counts = Counter(PurePosixPath(path).suffix or "<no suffix>" for path in test_paths)
    python_paths = [path for path in test_paths if path.endswith(".py")]
    manifest = {}
    rows = {
        "asyncio_decorators": [],
        "async_test_defs": [],
        "pytest_param": [],
        "pytest_raises": [],
        "autouse_fixtures": [],
    }
    parse_errors = []

    for path in python_paths:
        source_bytes = git_bytes("show", f"{source_sha}:{path}")
        source = source_bytes.decode()
        manifest[path] = hashlib.sha256(source_bytes).hexdigest()
        try:
            file_rows = analyze_source(path, source)
        except SyntaxError as error:
            parse_errors.append({"path": path, "line": error.lineno, "error": error.msg})
            continue
        for name, values in file_rows.items():
            rows[name].extend({"path": path, **value} for value in values)

    return {
        "source_sha": source_sha,
        "scope": "AST syntax inventory of tracked Python files under tests",
        "tracked_test_path_count": len(tree_paths),
        "tracked_test_suffix_counts": dict(sorted(suffix_counts.items())),
        "excluded_var_paths": excluded_var_paths,
        "parsed_python_file_count": len(manifest),
        "parse_errors": parse_errors,
        "sha256_manifest_by_path": manifest,
        "manifest_digest": hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "counts": {
            "asyncio_decorators": len(rows["asyncio_decorators"]),
            "async_test_defs": len(rows["async_test_defs"]),
            "pytest_param_calls": len(rows["pytest_param"]),
            "pytest_param_with_literal_id_keyword": sum(row["has_literal_id_keyword"] for row in rows["pytest_param"]),
            "pytest_param_without_literal_id_keyword": sum(
                not row["has_literal_id_keyword"] for row in rows["pytest_param"]
            ),
            "pytest_raises_calls": len(rows["pytest_raises"]),
            "pytest_raises_with_literal_match_keyword": sum(
                row["has_literal_match_keyword"] for row in rows["pytest_raises"]
            ),
            "pytest_raises_without_literal_match_keyword": sum(
                not row["has_literal_match_keyword"] for row in rows["pytest_raises"]
            ),
            "pytest_raises_with_keyword_expansion": sum(row["has_keyword_expansion"] for row in rows["pytest_raises"]),
            "autouse_fixtures": len(rows["autouse_fixtures"]),
            "autouse_fixtures_with_yield": sum(row["yield_count"] > 0 for row in rows["autouse_fixtures"]),
            "autouse_fixtures_without_yield": sum(row["yield_count"] == 0 for row in rows["autouse_fixtures"]),
        },
        "rows": rows,
        "syntax_limits": [
            "Imported pytest aliases are recognized syntactically; alias rebinding is not resolved.",
            "Keyword expansions and dynamically assembled decorators are not interpreted.",
            "Missing id= or match= means the literal keyword is absent from the AST.",
            "Yield counts describe syntax and do not establish teardown behavior.",
            "No repository tests or runtime behavior are executed.",
        ],
        "no_claim": [
            "This inventory does not establish behavior coverage or branch coverage.",
            "It does not establish teardown resilience or test adequacy.",
            "It makes no timing, speedup, or test-removal claim.",
        ],
    }


def probe_detectors():
    snippets = {
        "negative_missing_id_and_match": """import pytest
@pytest.mark.parametrize("value", [pytest.param(1, id="named"), pytest.param(2)])
def test_negative(value):
    with pytest.raises(ValueError):
        raise ValueError("planned")
""",
        "positive_direct_asyncio": """import pytest
@pytest.mark.asyncio
async def test_direct_asyncio():
    pass
""",
        "positive_aliased_asyncio": """import pytest as pt
@pt.mark.asyncio
async def test_aliased_asyncio():
    pass
""",
        "fixtures_with_and_without_yield": """import pytest as pt
@pt.fixture(autouse=True)
def teardown_fixture():
    yield
    release()
@pt.fixture(autouse=True)
def no_yield_fixture():
    pass
""",
        "positive_import_aliases": """import pytest as pt
from pytest import param as case, raises as expect, fixture as shared
@shared(autouse=True)
def shared_cleanup():
    yield
    release()
@pt.mark.parametrize("value", [case(1, id="first case")])
def test_positive(value):
    with expect(ValueError, match="planned"):
        raise ValueError("planned")
""",
    }
    results = {name: analyze_source(f"<memory:{name}>", source) for name, source in snippets.items()}
    negative = results["negative_missing_id_and_match"]
    assert [row["has_literal_id_keyword"] for row in negative["pytest_param"]] == [
        True,
        False,
    ]
    assert [row["has_literal_match_keyword"] for row in negative["pytest_raises"]] == [False]
    for name in ("positive_direct_asyncio", "positive_aliased_asyncio"):
        assert len(results[name]["asyncio_decorators"]) == 1
        assert len(results[name]["async_test_defs"]) == 1
    fixture_counts = [row["yield_count"] for row in results["fixtures_with_and_without_yield"]["autouse_fixtures"]]
    assert fixture_counts == [1, 0]
    aliases = results["positive_import_aliases"]
    assert aliases["pytest_param"][0]["has_literal_id_keyword"]
    assert aliases["pytest_raises"][0]["has_literal_match_keyword"]
    assert aliases["autouse_fixtures"][0]["yield_count"] == 1
    return results


def write_lossless_gzip(path, document):
    raw = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()
    compressed = gzip.compress(raw, mtime=0)
    path.write_bytes(compressed)
    if gzip.decompress(path.read_bytes()) != raw:
        raise RuntimeError("compressed inventory failed byte-equality verification")
    return hashlib.sha256(compressed).hexdigest(), hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", default=DEFAULT_SOURCE_SHA)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("pytest-syntax-inventory.json.gz"),
    )
    args = parser.parse_args()
    resolved_sha = git_bytes("rev-parse", "--verify", f"{args.source_sha}^{{commit}}").decode().strip()
    document = inventory(resolved_sha)
    document["probe_results"] = probe_detectors()
    if document["parse_errors"]:
        raise RuntimeError(f"AST parse errors: {document['parse_errors']}")
    compressed_sha, json_sha = write_lossless_gzip(args.output, document)
    print(
        json.dumps(
            {
                "source_sha": document["source_sha"],
                "tracked_test_path_count": document["tracked_test_path_count"],
                "parsed_python_file_count": document["parsed_python_file_count"],
                "excluded_var_path_count": len(document["excluded_var_paths"]),
                "manifest_digest": document["manifest_digest"],
                "counts": document["counts"],
                "compressed_sha256": compressed_sha,
                "json_sha256": json_sha,
                "output": str(args.output),
                "probe_results": {
                    name: {
                        "asyncio_decorators": len(rows["asyncio_decorators"]),
                        "async_test_defs": len(rows["async_test_defs"]),
                        "param_id_keywords": [row["has_literal_id_keyword"] for row in rows["pytest_param"]],
                        "raises_match_keywords": [row["has_literal_match_keyword"] for row in rows["pytest_raises"]],
                        "autouse_yield_counts": [row["yield_count"] for row in rows["autouse_fixtures"]],
                    }
                    for name, rows in document["probe_results"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

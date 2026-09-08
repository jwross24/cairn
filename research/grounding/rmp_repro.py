"""Exit 0 while Tier-3 admission is unreachable from every real launch adapter.

The adapters expose a declared tier and the gate honors it, so the remaining hold is that no
production caller ever declares above Tier 0. This probe goes nonzero the day one does, which is
the observable `cairn-ziz` lands on.
"""

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2] / "src" / "cairn"


def _module_constants(tree):
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value.value
    return found


def _parameter_defaults(tree, consts):
    """Every `declared_tier` parameter's default, resolved through module constants."""
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        args = node.args
        positional = args.posonlyargs + args.args
        for name, default in list(zip(positional[len(positional) - len(args.defaults) :], args.defaults)) + list(
            zip(args.kwonlyargs, args.kw_defaults)
        ):
            if name.arg != "declared_tier" or default is None:
                continue
            if isinstance(default, ast.Constant):
                found[node.name] = default.value
            elif isinstance(default, ast.Name):
                found[node.name] = consts.get(default.id, f"<{default.id}>")
    return found


def _enclosing(tree, target):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and any(child is target for child in ast.walk(node)):
            return node.name
    return None


def declared_tiers(path):
    """Every declared tier a module can hand the gate, resolved to a literal where one exists."""
    tree = ast.parse((ROOT / path).read_text())
    consts = _module_constants(tree)
    defaults = _parameter_defaults(tree, consts)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "declared_tier":
                continue
            value = kw.value
            if isinstance(value, ast.Constant):
                found.append(value.value)
            elif isinstance(value, ast.Name) and value.id in consts:
                found.append(consts[value.id])
            elif isinstance(value, ast.Name):
                found.append(defaults.get(_enclosing(tree, node), f"<{value.id}>"))
    return found


def calls(path, name, attribute=None):
    tree = ast.parse((ROOT / path).read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == name:
            if attribute is None or (isinstance(func.value, ast.Name) and func.value.id == attribute):
                yield node
        elif isinstance(func, ast.Name) and func.id == name and attribute is None:
            yield node


modules = sorted(p.name for p in ROOT.glob("*.py") if any(calls(p.name, "launch", "runner")))
print(f"modules calling runner.launch: {modules}")

adapters = sorted(module.name for module in ROOT.glob("*.py") if any(calls(module.name, "launch_trial", "instances")))
tiers = {name: declared_tiers(name) for name in sorted(set(modules) | set(adapters))}
print(f"declared tiers every launch path can hand the gate: {tiers}")

flat = [tier for values in tiers.values() for tier in values]
above_zero = [tier for tier in flat if tier != 0]
print(f"declared tiers above 0 on a launch path: {above_zero}")

source = (ROOT / "tiergate.py").read_text()
gate_zero = "if launch.declared_tier == 0:\n            return None" in source
print(f"_selected_ticket returns None for declared_tier 0: {gate_zero}")

unreachable = bool(flat) and not above_zero and gate_zero
print()
print(f"VERDICT unreachable: {unreachable}")
sys.exit(0 if unreachable else 1)

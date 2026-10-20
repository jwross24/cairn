import re

from cairn.sql_lex import masked_text, significant_text, tokens

_NAME = r'(?:"(?:[^"]|"")+"|\w+)'
_CONSTANT = r"(?:NULL|[-+]?\d+(?:\.\d+)?|'(?:[^']|'')*')"
_TABLE = re.compile(rf"CREATE TABLE (?:IF NOT EXISTS )?{_NAME} ?\(", re.IGNORECASE)
_INDEX = re.compile(rf"CREATE (?:UNIQUE )?INDEX (?:IF NOT EXISTS )?{_NAME} ON {_NAME} ?\(", re.IGNORECASE)
_VIEW = re.compile(rf"CREATE VIEW (?:IF NOT EXISTS )?{_NAME} AS SELECT\b", re.IGNORECASE)
_TRIGGER_HEAD = re.compile(rf"CREATE TRIGGER (?:IF NOT EXISTS )?{_NAME} (?:BEFORE|AFTER|INSTEAD OF) ", re.IGNORECASE)
_ALTER = re.compile(rf"ALTER TABLE {_NAME} ADD COLUMN {_NAME}(.*)$", re.IGNORECASE)
_DEFAULT = re.compile(rf"\bDEFAULT\s+({_CONSTANT})(?=\s|$|,)", re.IGNORECASE)
_FORBIDDEN_COLUMN_CLAUSE = re.compile(r"\b(?:PRIMARY\s+KEY|UNIQUE|REFERENCES|GENERATED|AS)\b", re.IGNORECASE)
_RAISE_ONLY = re.compile(r"SELECT\s+RAISE\s*\(", re.IGNORECASE)


def _significant(token_list):
    return [t for t in token_list if t[0] not in ("space", "comment")]


def _words(token_list):
    return [t[1].upper() for t in _significant(token_list) if t[0] == "word"]


def _is_trigger(token_list):
    words = _words(token_list)[:3]
    return (
        words[:2] == ["CREATE", "TRIGGER"]
        or words[:3] == ["CREATE", "TEMP", "TRIGGER"]
        or words[:3] == ["CREATE", "TEMPORARY", "TRIGGER"]
    )


def _statement_tokens(sql):
    statements, current = [], []
    case_depth, begun, ended = 0, False, False
    for token in tokens(sql):
        kind, text = token
        upper = text.upper() if kind == "word" else ""
        if kind == "punct" and text == ";" and (not _is_trigger(current) or ended):
            statements.append(current)
            current, case_depth, begun, ended = [], 0, False, False
            continue
        current.append(token)
        if _is_trigger(current):
            if upper == "BEGIN" and not begun:
                begun = True
            elif upper == "CASE":
                case_depth += 1
            elif upper == "END":
                if case_depth:
                    case_depth -= 1
                elif begun:
                    ended = True
    statements.append(current)
    return [s for s in statements if _significant(s)]


def split_statements(sql):
    return ["".join(text for _, text in statement).strip() for statement in _statement_tokens(sql)]


def _body_statements(body):
    statements, current, case_depth = [], [], 0
    for token in body:
        kind, text = token
        upper = text.upper() if kind == "word" else ""
        if kind == "punct" and text == ";" and not case_depth:
            statements.append(current)
            current = []
            continue
        current.append(token)
        if upper == "CASE":
            case_depth += 1
        elif upper == "END" and case_depth:
            case_depth -= 1
    statements.append(current)
    return [s for s in statements if _significant(s)]


def _trigger_problems(statement):
    if any(kind == "unterminated" for kind, _ in statement):
        return ["trigger holds an unterminated quote or comment"]
    positions = [i for i, (kind, _) in enumerate(statement) if kind not in ("space", "comment")]
    begin = next((i for i in positions if statement[i][0] == "word" and statement[i][1].upper() == "BEGIN"), None)
    end = positions[-1]
    if begin is None or begin == end or not (statement[end][0] == "word" and statement[end][1].upper() == "END"):
        return ["trigger has no BEGIN ... END body"]
    if not _TRIGGER_HEAD.match(masked_text(statement[:begin]) + " "):
        return ["trigger header is not CREATE TRIGGER name BEFORE|AFTER|INSTEAD OF"]
    problems = []
    for inner in _body_statements(statement[begin + 1 : end]):
        text = significant_text(inner)
        if not _RAISE_ONLY.match(text):
            problems.append(f"trigger body statement is not SELECT RAISE: {text[:60]}")
    return problems


def _alter_problems(tail, masked_tail):
    problems = []
    default = _DEFAULT.search(tail)
    not_null = re.search(r"\bNOT\s+NULL\b", masked_tail, re.IGNORECASE)
    if _FORBIDDEN_COLUMN_CLAUSE.search(masked_tail):
        problems.append("ADD COLUMN may carry only a type, NOT NULL, a constant DEFAULT and CHECK")
    if re.search(r"\bDEFAULT\b", masked_tail, re.IGNORECASE) and not default:
        problems.append("ADD COLUMN default is not a constant")
    if not_null and (not default or default.group(1).upper() == "NULL"):
        problems.append("ADD COLUMN NOT NULL needs a non-NULL constant DEFAULT")
    return problems


def lint(sql):
    problems, has_trigger = [], False
    statements = _statement_tokens(sql)
    if not statements:
        problems.append("the migration holds no statement")
    for statement in statements:
        text = significant_text(statement)
        masked = masked_text(statement)
        head = text.split(" ", 1)[0].upper() if text else ""
        if any(kind == "unterminated" for kind, _ in statement):
            problems.append(f"unterminated quote or comment: {text[:60]}")
        elif _is_trigger(statement):
            has_trigger = True
            problems += _trigger_problems(statement)
        elif (alter := _ALTER.fullmatch(text)) and (alter_masked := _ALTER.fullmatch(masked)):
            problems += _alter_problems(alter.group(1), alter_masked.group(1))
        elif not any(p.match(text) for p in (_TABLE, _INDEX, _VIEW)):
            problems.append(f"{head or 'empty'} is not additive: {text[:60]}")
    return problems, has_trigger

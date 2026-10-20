QUOTES = {"'": "string", '"': "identifier", "`": "identifier"}


def _quoted_end(sql, start, quote):
    i, n = start + 1, len(sql)
    while i < n:
        if sql[i] == quote:
            if i + 1 < n and sql[i + 1] == quote:
                i += 2
                continue
            return i + 1, True
        i += 1
    return n, False


def _word_end(sql, start):
    i, n = start, len(sql)
    while i < n and (sql[i].isalnum() or sql[i] in "_$"):
        i += 1
    return i


def tokens(sql):
    out, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if c.isspace():
            j = i
            while j < n and sql[j].isspace():
                j += 1
            out.append(("space", sql[i:j]))
        elif c in QUOTES:
            j, closed = _quoted_end(sql, i, c)
            out.append((QUOTES[c] if closed else "unterminated", sql[i:j]))
        elif c == "[":
            close = sql.find("]", i + 1)
            j = n if close < 0 else close + 1
            out.append(("identifier" if close >= 0 else "unterminated", sql[i:j]))
        elif sql.startswith("--", i):
            close = sql.find("\n", i)
            j = n if close < 0 else close
            out.append(("comment", sql[i:j]))
        elif sql.startswith("/*", i):
            close = sql.find("*/", i + 2)
            j = n if close < 0 else close + 2
            out.append(("comment" if close >= 0 else "unterminated", sql[i:j]))
        elif c.isalnum() or c in "_$":
            j = _word_end(sql, i)
            out.append(("word", sql[i:j]))
        else:
            j = i + 1
            out.append(("punct", c))
        i = j
    return out


def normalize_sql(sql):
    pieces = []
    for kind, text in tokens(sql):
        if kind == "space":
            if pieces and pieces[-1] != " ":
                pieces.append(" ")
        else:
            pieces.append(" ".join(text.split()) if kind == "comment" else text)
    if pieces and pieces[-1] == " ":
        pieces.pop()
    return "".join(pieces)


def significant_text(token_list):
    return normalize_sql("".join(" " if kind == "comment" else text for kind, text in token_list))


def masked_text(token_list):
    return significant_text(
        [("word", "Q0") if kind in ("string", "identifier") else (kind, text) for kind, text in token_list]
    )

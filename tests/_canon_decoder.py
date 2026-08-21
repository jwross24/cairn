from cairn import canon, keys

REGISTRY = {s.name: s for s in (*keys.SCHEMAS.values(), keys.METHOD_IDENTITY)}


def _u64(buf, i):
    return int.from_bytes(buf[i : i + 8], "little"), i + 8


def _int(buf, i):
    sign = buf[i]
    i += 1
    n, i = _u64(buf, i)
    value = int.from_bytes(buf[i : i + n], "big") if n else 0
    return (-value if sign else value), i + n


def decode_value(buf, i=0):
    tag = buf[i : i + 1]
    i += 1
    if tag == canon.TAG_INT:
        return _int(buf, i)
    if tag == canon.TAG_STR:
        n, i = _u64(buf, i)
        return buf[i : i + n].decode("utf-8"), i + n
    if tag == canon.TAG_BYTES:
        n, i = _u64(buf, i)
        return bytes(buf[i : i + n]), i + n
    if tag == canon.TAG_BOOL:
        return buf[i] == 1, i + 1
    if tag == canon.TAG_NONE:
        return None, i
    if tag in (canon.TAG_LIST, canon.TAG_SET):
        n, i = _u64(buf, i)
        items = []
        for _ in range(n):
            v, i = decode_value(buf, i)
            items.append(v)
        return items, i
    if tag == canon.TAG_MAP:
        n, i = _u64(buf, i)
        out = {}
        for _ in range(n):
            k, i = decode_value(buf, i)
            v, i = decode_value(buf, i)
            out[k] = v
        return out, i
    if tag == canon.TAG_BLOBREF:
        n, i = _u64(buf, i)
        digest = bytes(buf[i : i + n]).hex()
        i += n
        size, i = _int(buf, i)
        return [digest, size], i
    if tag == canon.TAG_STRUCT:
        name, i = decode_value(buf, i)
        out = {}
        for field in REGISTRY[name].fields:
            out[field.name], i = decode_value(buf, i)
        return out, i
    raise ValueError(f"unknown tag {tag!r} at {i - 1}")


def decode(buf):
    value, end = decode_value(buf, 0)
    if end != len(buf):
        raise ValueError(f"trailing bytes after offset {end}")
    return value


def decode_int(body):
    value, end = _int(body, 0)
    if end != len(body):
        raise ValueError("trailing bytes")
    return value

import unicodedata
from dataclasses import dataclass

import blake3

TAG_INT = b"\x01"
TAG_STR = b"\x02"
TAG_BYTES = b"\x03"
TAG_BOOL = b"\x04"
TAG_NONE = b"\x05"
TAG_LIST = b"\x06"
TAG_MAP = b"\x07"
TAG_SET = b"\x08"
TAG_STRUCT = b"\x09"
TAG_BLOBREF = b"\x0a"
DIGEST_BYTES = 32


class CanonError(ValueError):
    pass


class Type:
    def encode(self, value):
        raise NotImplementedError

    def decode_at(self, data, i):
        raise NotImplementedError


class _Int(Type):
    def encode(self, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise CanonError(f"expected int, got {type(value).__name__}")
        return TAG_INT + encode_int_body(value)

    def decode_at(self, data, i):
        return decode_int_body(data, _expect(data, i, TAG_INT, "int"))


class _Str(Type):
    def encode(self, value):
        if not isinstance(value, str):
            raise CanonError(f"expected str, got {type(value).__name__}")
        try:
            data = unicodedata.normalize("NFC", value).encode("utf-8")
        except UnicodeEncodeError as exc:
            raise CanonError(f"string is not UTF-8 encodable: {exc.reason}") from None
        return TAG_STR + length_prefix(data)

    def decode_at(self, data, i):
        body, i = _read_prefixed(data, _expect(data, i, TAG_STR, "str"))
        try:
            return body.decode("utf-8"), i
        except UnicodeDecodeError as exc:
            raise CanonError(f"string is not UTF-8: {exc.reason}") from None


class _NonEmptyStr(_Str):
    def encode(self, value):
        if isinstance(value, str) and not value:
            raise CanonError("must not be empty")
        return super().encode(value)


class _Bytes(Type):
    def encode(self, value):
        if not isinstance(value, (bytes, bytearray)):
            raise CanonError(f"expected bytes, got {type(value).__name__}")
        return TAG_BYTES + length_prefix(bytes(value))

    def decode_at(self, data, i):
        return _read_prefixed(data, _expect(data, i, TAG_BYTES, "bytes"))


class _Bool(Type):
    def encode(self, value):
        if not isinstance(value, bool):
            raise CanonError(f"expected bool, got {type(value).__name__}")
        return TAG_BOOL + (b"\x01" if value else b"\x00")

    def decode_at(self, data, i):
        i = _expect(data, i, TAG_BOOL, "bool")
        flag = data[i : i + 1]
        if flag not in (b"\x00", b"\x01"):
            raise CanonError(f"bool body {flag!r} at offset {i}")
        return flag == b"\x01", i + 1


class _Optional(Type):
    def __init__(self, inner):
        self.inner = inner

    def encode(self, value):
        if value is None:
            return TAG_NONE
        return self.inner.encode(value)

    def decode_at(self, data, i):
        if data[i : i + 1] == TAG_NONE:
            return None, i + 1
        return self.inner.decode_at(data, i)


class _List(Type):
    def __init__(self, elem):
        self.elem = elem

    def encode(self, value):
        if not isinstance(value, (list, tuple)):
            raise CanonError(f"expected list, got {type(value).__name__}")
        parts = [self.elem.encode(v) for v in value]
        return TAG_LIST + u64le(len(parts)) + b"".join(parts)

    def decode_at(self, data, i):
        count, i = _read_u64(data, _expect(data, i, TAG_LIST, "list"))
        out = []
        for _ in range(count):
            value, i = self.elem.decode_at(data, i)
            out.append(value)
        return out, i


class _Set(Type):
    def __init__(self, elem):
        self.elem = elem

    def encode(self, value):
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise CanonError(f"expected set, got {type(value).__name__}")
        parts = sorted(self.elem.encode(v) for v in value)
        if len(set(parts)) != len(parts):
            raise CanonError("duplicate element in set")
        return TAG_SET + u64le(len(parts)) + b"".join(parts)

    def decode_at(self, data, i):
        count, i = _read_u64(data, _expect(data, i, TAG_SET, "set"))
        out = []
        for _ in range(count):
            value, i = self.elem.decode_at(data, i)
            out.append(value)
        return frozenset(out), i


class _Map(Type):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def encode(self, value):
        if not isinstance(value, dict):
            raise CanonError(f"expected map, got {type(value).__name__}")
        pairs = sorted((self.key.encode(k), self.value.encode(v)) for k, v in value.items())
        if len({k for k, _ in pairs}) != len(pairs):
            raise CanonError("duplicate key in map after canonicalization")
        return TAG_MAP + u64le(len(pairs)) + b"".join(k + v for k, v in pairs)

    def decode_at(self, data, i):
        count, i = _read_u64(data, _expect(data, i, TAG_MAP, "map"))
        out = {}
        for _ in range(count):
            key, i = self.key.decode_at(data, i)
            value, i = self.value.decode_at(data, i)
            out[key] = value
        return out, i


class _BlobRef(Type):
    def encode(self, value):
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise CanonError("blob reference must be (hash, size)")
        digest, size = value
        if isinstance(digest, str):
            try:
                raw = bytes.fromhex(digest)
            except ValueError:
                raise CanonError("blob reference hash must be hex") from None
        elif isinstance(digest, (bytes, bytearray)):
            raw = bytes(digest)
        else:
            raise CanonError(f"blob reference hash must be hex str or bytes, got {type(digest).__name__}")
        if len(raw) != DIGEST_BYTES:
            raise CanonError("blob reference hash must be 32 bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise CanonError("blob reference size must be a non-negative int")
        return TAG_BLOBREF + length_prefix(raw) + encode_int_body(size)

    def decode_at(self, data, i):
        raw, i = _read_prefixed(data, _expect(data, i, TAG_BLOBREF, "blob reference"))
        if len(raw) != DIGEST_BYTES:
            raise CanonError("blob reference hash must be 32 bytes")
        size, i = decode_int_body(data, i)
        return (raw.hex(), size), i


@dataclass(frozen=True)
class Field:
    name: str
    type: Type


class Struct(Type):
    def __init__(self, name, fields):
        self.name = name
        self.fields = tuple(fields)
        self.names = tuple(f.name for f in self.fields)

    def encode(self, value):
        if not isinstance(value, dict):
            raise CanonError(f"{self.name}: expected a mapping, got {type(value).__name__}")
        unknown = sorted(set(value) - set(self.names))
        if unknown:
            raise CanonError(f"{self.name}: undeclared field(s) {unknown}")
        missing = [n for n in self.names if n not in value]
        if missing:
            raise CanonError(f"{self.name}: missing field(s) {missing}")
        out = [TAG_STRUCT, STR.encode(self.name)]
        for field in self.fields:
            try:
                out.append(field.type.encode(value[field.name]))
            except CanonError as exc:
                raise CanonError(f"{self.name}.{field.name}: {exc}") from None
        return b"".join(out)

    def decode_at(self, data, i):
        name, i = STR.decode_at(data, _expect(data, i, TAG_STRUCT, f"struct {self.name}"))
        if name != self.name:
            raise CanonError(f"expected struct {self.name}, got {name}")
        out = {}
        for field in self.fields:
            out[field.name], i = field.type.decode_at(data, i)
        return out, i


INT = _Int()
STR = _Str()
NON_EMPTY_STR = _NonEmptyStr()
BYTES = _Bytes()
BOOL = _Bool()
BLOBREF = _BlobRef()


def Optional(inner):
    return _Optional(inner)


def List(elem):
    return _List(elem)


def Set(elem):
    return _Set(elem)


def Map(key, value):
    return _Map(key, value)


def u64le(n):
    if n < 0 or n >= 1 << 64:
        raise CanonError("length out of u64 range")
    return n.to_bytes(8, "little")


def length_prefix(data):
    return u64le(len(data)) + data


def encode_int_body(value):
    if isinstance(value, float):
        raise CanonError("floats are not canonical")
    sign = b"\x01" if value < 0 else b"\x00"
    magnitude = abs(value)
    body = magnitude.to_bytes((magnitude.bit_length() + 7) // 8, "big") if magnitude else b""
    return sign + length_prefix(body)


def reject_floats(value, path="$"):
    if isinstance(value, float):
        raise CanonError(f"{path}: floats are not canonical")
    if isinstance(value, dict):
        for k, v in value.items():
            reject_floats(k, f"{path}.{k}")
            reject_floats(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple, set, frozenset)):
        for i, v in enumerate(value):
            reject_floats(v, f"{path}[{i}]")


def _expect(data, i, tag, what):
    if data[i : i + 1] != tag:
        raise CanonError(f"expected {what} at offset {i}, got tag {data[i : i + 1]!r}")
    return i + 1


def _read_u64(data, i):
    if i + 8 > len(data):
        raise CanonError(f"truncated length at offset {i}")
    return int.from_bytes(data[i : i + 8], "little"), i + 8


def _read_prefixed(data, i):
    length, i = _read_u64(data, i)
    if i + length > len(data):
        raise CanonError(f"truncated body at offset {i}")
    return bytes(data[i : i + length]), i + length


def decode_int_body(data, i):
    sign = data[i : i + 1]
    if sign not in (b"\x00", b"\x01"):
        raise CanonError(f"int sign {sign!r} at offset {i}")
    body, i = _read_prefixed(data, i + 1)
    if body[:1] == b"\x00":
        raise CanonError("int magnitude carries a leading zero byte")
    value = int.from_bytes(body, "big") if body else 0
    if sign == b"\x01" and value == 0:
        raise CanonError("negative zero is not canonical")
    return (-value if sign == b"\x01" else value), i


def encode(schema, value):
    reject_floats(value)
    return schema.encode(value)


def decode(schema, data):
    data = bytes(data)
    value, end = schema.decode_at(data, 0)
    if end != len(data):
        raise CanonError(f"trailing bytes after offset {end}")
    return value


def digest(domain_tag, canonical_bytes):
    if not isinstance(domain_tag, str) or not domain_tag:
        raise CanonError("domain tag must be a non-empty str")
    return blake3.blake3(domain_tag.encode("utf-8") + b"\x00" + canonical_bytes).hexdigest()


def hash_object(domain_tag, schema, value):
    return digest(domain_tag, encode(schema, value))

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


class _Int(Type):
    def encode(self, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise CanonError(f"expected int, got {type(value).__name__}")
        return TAG_INT + encode_int_body(value)


class _Str(Type):
    def encode(self, value):
        if not isinstance(value, str):
            raise CanonError(f"expected str, got {type(value).__name__}")
        try:
            data = unicodedata.normalize("NFC", value).encode("utf-8")
        except UnicodeEncodeError as exc:
            raise CanonError(f"string is not UTF-8 encodable: {exc.reason}") from None
        return TAG_STR + length_prefix(data)


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


class _Bool(Type):
    def encode(self, value):
        if not isinstance(value, bool):
            raise CanonError(f"expected bool, got {type(value).__name__}")
        return TAG_BOOL + (b"\x01" if value else b"\x00")


class _Optional(Type):
    def __init__(self, inner):
        self.inner = inner

    def encode(self, value):
        if value is None:
            return TAG_NONE
        return self.inner.encode(value)


class _List(Type):
    def __init__(self, elem):
        self.elem = elem

    def encode(self, value):
        if not isinstance(value, (list, tuple)):
            raise CanonError(f"expected list, got {type(value).__name__}")
        parts = [self.elem.encode(v) for v in value]
        return TAG_LIST + u64le(len(parts)) + b"".join(parts)


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


def encode(schema, value):
    reject_floats(value)
    return schema.encode(value)


def digest(domain_tag, canonical_bytes):
    if not isinstance(domain_tag, str) or not domain_tag:
        raise CanonError("domain tag must be a non-empty str")
    return blake3.blake3(domain_tag.encode("utf-8") + b"\x00" + canonical_bytes).hexdigest()


def hash_object(domain_tag, schema, value):
    return digest(domain_tag, encode(schema, value))

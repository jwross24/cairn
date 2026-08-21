import itertools
from contextlib import contextmanager

import blake3

from cairn import canon


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def dict_order_encoder():
    def encode(self, value):
        pairs = [(self.key.encode(k), self.value.encode(v)) for k, v in value.items()]
        return canon.TAG_MAP + canon.u64le(len(pairs)) + b"".join(k + v for k, v in pairs)

    with _swap(canon._Map, "encode", encode):
        yield


@contextmanager
def salted_encoder():
    counter = itertools.count()
    real = canon.encode

    def encode(schema, value):
        return real(schema, value) + bytes([next(counter) % 256])

    with _swap(canon, "encode", encode):
        yield


@contextmanager
def concat_encoder():
    with _swap(canon, "length_prefix", lambda data: data):
        yield


@contextmanager
def untagged_hasher():
    with _swap(canon, "digest", lambda tag, canonical: blake3.blake3(canonical).hexdigest()):
        yield


@contextmanager
def first_n_fields_encoder():
    def encode(self, value):
        out = [canon.TAG_STRUCT, canon.STR.encode(self.name)]
        for field in self.fields[:-1]:
            out.append(field.type.encode(value[field.name]))
        return b"".join(out)

    with _swap(canon.Struct, "encode", encode):
        yield


@contextmanager
def fixed_width_int_encoder():
    def body(value):
        sign = b"\x01" if value < 0 else b"\x00"
        magnitude = abs(value) & (2**64 - 1)
        return sign + canon.length_prefix(magnitude.to_bytes(8, "big"))

    with _swap(canon, "encode_int_body", body):
        yield


ALL = {
    "dict_order_encoder": dict_order_encoder,
    "salted_encoder": salted_encoder,
    "concat_encoder": concat_encoder,
    "untagged_hasher": untagged_hasher,
    "first_n_fields_encoder": first_n_fields_encoder,
    "fixed_width_int_encoder": fixed_width_int_encoder,
}

from cairn import canon
from cairn.canon import BLOBREF, INT, NON_EMPTY_STR, STR, Field, List, Map, Optional, Struct

TAG_RECIPE_KEY = "cairn/recipe-key/v1"
TAG_HYPOTHESIS_KEY = "cairn/hypothesis-key/v1"
TAG_NODE = "cairn/node/v1"
TAG_IDENTITY_BUNDLE = "cairn/identity-bundle/v1"
TAG_ENV_MANIFEST = "cairn/env-manifest/v1"
TAG_SELFTEST_CERT = "cairn/selftest-cert/v1"
TAG_GATE_BUNDLE = "cairn/gate-bundle/v1"
TAG_INSTANCE = "cairn/instance/v1"
TAG_CHAIN = "cairn/chain/v1"
DOMAIN_TAGS = (
    TAG_RECIPE_KEY,
    TAG_HYPOTHESIS_KEY,
    TAG_NODE,
    TAG_IDENTITY_BUNDLE,
    TAG_ENV_MANIFEST,
    TAG_SELFTEST_CERT,
    TAG_GATE_BUNDLE,
    TAG_INSTANCE,
    TAG_CHAIN,
)

ENV_MANIFEST = Struct(
    "env_manifest",
    [
        Field("os", STR),
        Field("python", STR),
        Field("cypari2", STR),
        Field("libpari", STR),
        Field("blake3", STR),
        Field("gp_binary_sha256", STR),
    ],
)

IDENTITY_BUNDLE = Struct(
    "identity_bundle",
    [
        Field("interface_version", STR),
        Field("implementation_revision", STR),
        Field("tool_digests", Map(STR, STR)),
        Field("container_digest", NON_EMPTY_STR),
        Field("numeric_profile", Optional(STR)),
    ],
)

RECIPE = Struct(
    "recipe",
    [
        Field("skill_identity_hash", STR),
        Field("inputs", Map(STR, BLOBREF)),
        Field("seed", INT),
        Field("tool_versions", Map(STR, STR)),
        Field("container_digest", NON_EMPTY_STR),
        Field("salt", STR),
    ],
)

METHOD_IDENTITY = Struct(
    "method_identity",
    [
        Field("interface_version", STR),
        Field("params", Map(STR, STR)),
    ],
)

HYPOTHESIS_OBJECT = Struct(
    "hypothesis_object",
    [
        Field("target_family", STR),
        Field("claimed", Map(STR, STR)),
        Field("method_identity", METHOD_IDENTITY),
        Field("declared_parameter_ranges", Map(STR, List(INT))),
        Field("sampling_distribution", Optional(STR)),
    ],
)

SELFTEST_CERT = Struct(
    "selftest_cert",
    [
        Field("identity_bundle_hash", STR),
        Field("transcript_hash", STR),
        Field("env_manifest_hash", STR),
    ],
)

INSTANCE = Struct(
    "instance",
    [
        Field("p", INT),
        Field("a", INT),
        Field("b", INT),
        Field("n", INT),
        Field("P", List(INT)),
        Field("Q", List(INT)),
    ],
)


def env_manifest_digest(manifest):
    return canon.hash_object(TAG_ENV_MANIFEST, ENV_MANIFEST, manifest)


def identity_bundle_hash(bundle):
    return canon.hash_object(TAG_IDENTITY_BUNDLE, IDENTITY_BUNDLE, bundle)


def recipe_key(recipe):
    return canon.hash_object(TAG_RECIPE_KEY, RECIPE, recipe)


def hypothesis_key(hypothesis):
    return canon.hash_object(TAG_HYPOTHESIS_KEY, HYPOTHESIS_OBJECT, hypothesis)


def instance_hash(instance):
    return canon.hash_object(TAG_INSTANCE, INSTANCE, instance)


def selftest_cert_hash(cert):
    return canon.hash_object(TAG_SELFTEST_CERT, SELFTEST_CERT, cert)


def node_hash(kind, canonical_bytes):
    return canon.digest(TAG_NODE, canon.encode(STR, kind) + canonical_bytes)


SCHEMAS = {
    "env_manifest": ENV_MANIFEST,
    "identity_bundle": IDENTITY_BUNDLE,
    "recipe": RECIPE,
    "hypothesis_object": HYPOTHESIS_OBJECT,
    "instance": INSTANCE,
    "selftest_cert": SELFTEST_CERT,
}

HASHERS = {
    "env_manifest": env_manifest_digest,
    "identity_bundle": identity_bundle_hash,
    "recipe": recipe_key,
    "hypothesis_object": hypothesis_key,
    "instance": instance_hash,
    "selftest_cert": selftest_cert_hash,
}
TAGS_BY_KIND = {
    "env_manifest": TAG_ENV_MANIFEST,
    "identity_bundle": TAG_IDENTITY_BUNDLE,
    "recipe": TAG_RECIPE_KEY,
    "hypothesis_object": TAG_HYPOTHESIS_KEY,
    "instance": TAG_INSTANCE,
    "selftest_cert": TAG_SELFTEST_CERT,
}

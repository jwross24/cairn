from cairn import substrate

HYPOTHESIS_ABSENT = "hypothesis-absent"
COMMITMENT_ABSENT = "entropy-commitment-absent"
HYPOTHESIS_AFTER_ENTROPY = "hypothesis-after-entropy"
NONCE_ABSENT = "nonce-absent"
NONCE_FOREIGN = "nonce-names-another-hypothesis"
NONCE_PUBLISHED = "nonce-published"
ARM_UNKNOWN = "arm-unknown"
METHOD_IDENTITY_MISMATCH = "method-identity-mismatch"
BASELINE_REVISION_MISMATCH = "baseline-revision-mismatch"
UNCERTIFIED_REVISION = "uncertified-revision"
YANKED_REVISION = "yanked-revision"
ALLOW_LIST_UNBOUND = "allow-list-unbound"
SUBSTRATE_READABLE = "substrate-readable"
PRE_SPAWN_REASONS = (
    HYPOTHESIS_ABSENT,
    COMMITMENT_ABSENT,
    HYPOTHESIS_AFTER_ENTROPY,
    NONCE_ABSENT,
    NONCE_FOREIGN,
    NONCE_PUBLISHED,
    ARM_UNKNOWN,
    METHOD_IDENTITY_MISMATCH,
    BASELINE_REVISION_MISMATCH,
    UNCERTIFIED_REVISION,
    YANKED_REVISION,
    ALLOW_LIST_UNBOUND,
    SUBSTRATE_READABLE,
)

ARMS_MISSING = "arms-missing"
TIER_REFUSED = "tier-refused"
INSTANCE_FAILED = "instance-failed"


class RunRefused(substrate.SubstrateError):
    def __init__(self, reason, detail):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")

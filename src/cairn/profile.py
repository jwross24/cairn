from collections.abc import Mapping
from dataclasses import dataclass


class ProfileUndeclared(LookupError):
    def __init__(self, bits, declared):
        super().__init__(f"cost profile declares no size {bits!r}; declared sizes: {sorted(declared)}")
        self.bits = bits
        self.declared = tuple(sorted(declared))


def declared_bits(inputs):
    """The size a launch's inputs name, or None where they name none.

    A launch carries its inputs either as the bare size or as a mapping holding one under `bits`;
    both shapes reach the gate, and every reader of a launch's size resolves it here so the tier
    gate and the ladder-rung predicate cannot disagree about what a launch declared.
    """
    if isinstance(inputs, Mapping):
        inputs = inputs.get("bits")
    if isinstance(inputs, bool) or not isinstance(inputs, int):
        return None
    return inputs


@dataclass(frozen=True)
class Evaluation:
    expected_wall_s: float
    expected_core_s: float
    expected_verification_core_s: float


@dataclass(frozen=True)
class SizeCost:
    mean_tries: float
    sd_tries: float
    per_try_s: float
    mean_wall_s: float


@dataclass(frozen=True)
class Production:
    model: str
    per_size: Mapping[int, SizeCost]


SAME_AS_PRODUCTION = "same_as_production"
CONSTANT = "constant"


@dataclass(frozen=True)
class Verification:
    grade: str
    cost_model: str
    core_s: float | None = None


@dataclass(frozen=True)
class MemoryProfile:
    """The table a skill keeps, as a shape the ladder's memory check can read.

    entries names the growth law in n, bytes_per_entry_bounds the declared span
    of the per-entry cost, and the measured maps hold what this machine showed at
    each size. A self-reported table size is a diagnostic; the gate's own RSS
    measurement is the predicate.
    """

    model: str
    entries: str
    bytes_per_entry_bounds: tuple[float, float]
    measured_bytes_per_entry: Mapping[int, float]
    measured_maxrss_bytes: Mapping[int, int]


@dataclass(frozen=True)
class CostProfile:
    tier: int
    production: Production
    verification: Verification
    source: str
    memory: MemoryProfile | None = None

    def declared_sizes(self):
        return tuple(sorted(self.production.per_size))

    def evaluate(self, bits):
        raw = bits.get("bits") if isinstance(bits, Mapping) else bits
        bits = declared_bits(bits)
        if bits is None or bits not in self.production.per_size:
            raise ProfileUndeclared(raw, self.production.per_size)
        cost = self.production.per_size[bits]
        wall = float(cost.mean_wall_s)
        if self.verification.cost_model == SAME_AS_PRODUCTION:
            return Evaluation(expected_wall_s=wall, expected_core_s=wall, expected_verification_core_s=wall)
        if self.verification.cost_model == CONSTANT:
            core_s = self.verification.core_s
            if isinstance(core_s, bool) or not isinstance(core_s, (int, float)) or not core_s > 0:
                raise ValueError(f"a constant verification cost model needs a positive core_s, got {core_s!r}")
            return Evaluation(expected_wall_s=wall, expected_core_s=wall, expected_verification_core_s=float(core_s))
        raise ValueError(f"unknown verification cost model {self.verification.cost_model!r}")

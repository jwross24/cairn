from collections.abc import Mapping
from dataclasses import dataclass


class ProfileUndeclared(LookupError):
    def __init__(self, bits, declared):
        super().__init__(f"cost profile declares no size {bits!r}; declared sizes: {sorted(declared)}")
        self.bits = bits
        self.declared = tuple(sorted(declared))


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


@dataclass(frozen=True)
class Verification:
    grade: str
    cost_model: str


@dataclass(frozen=True)
class CostProfile:
    tier: int
    production: Production
    verification: Verification
    source: str

    def declared_sizes(self):
        return tuple(sorted(self.production.per_size))

    def evaluate(self, bits):
        if isinstance(bits, Mapping):
            bits = bits.get("bits")
        if isinstance(bits, bool) or not isinstance(bits, int) or bits not in self.production.per_size:
            raise ProfileUndeclared(bits, self.production.per_size)
        cost = self.production.per_size[bits]
        wall = float(cost.mean_wall_s)
        if self.verification.cost_model != "same_as_production":
            raise ValueError(f"unknown verification cost model {self.verification.cost_model!r}")
        return Evaluation(expected_wall_s=wall, expected_core_s=wall, expected_verification_core_s=wall)

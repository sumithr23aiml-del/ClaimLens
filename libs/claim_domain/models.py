from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ClaimLine:
    description: str
    claimed_amount: Decimal
    admissible: bool = True


@dataclass(frozen=True)
class SettlementInput:
    lines: tuple[ClaimLine, ...]
    sum_insured: Decimal
    deductible: Decimal
    coinsurance_pct: Decimal = Decimal("0")
    sub_limit: Decimal | None = None
    depreciation_pct: Decimal = Decimal("0")


@dataclass(frozen=True)
class SettlementResult:
    claimed: Decimal
    inadmissible: Decimal
    depreciation: Decimal
    deductible: Decimal
    coinsurance: Decimal
    sub_limit_cap: Decimal
    sum_insured_cap: Decimal
    payable: Decimal
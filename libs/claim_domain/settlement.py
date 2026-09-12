from decimal import Decimal, ROUND_HALF_UP

from .models import SettlementInput, SettlementResult


ZERO = Decimal("0")
HUNDRED = Decimal("100")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_settlement(data: SettlementInput) -> SettlementResult:
    # 1. Total claimed amount
    claimed = money(
        sum((line.claimed_amount for line in data.lines), ZERO)
    )

    # 2. Remove inadmissible items
    admissible = ZERO
    inadmissible = ZERO

    for line in data.lines:
        if line.admissible:
            admissible += line.claimed_amount
        else:
            inadmissible += line.claimed_amount

    admissible = money(admissible)
    inadmissible = money(inadmissible)

    # 3. Apply depreciation
    depreciation = money(
        admissible * data.depreciation_pct / HUNDRED
    )

    after_depreciation = max(
        ZERO,
        admissible - depreciation,
    )

    # 4. Apply sub-limit
    sub_limit_cap = ZERO

    if data.sub_limit is not None:
        capped = min(after_depreciation, data.sub_limit)
        sub_limit_cap = money(after_depreciation - capped)
        after_depreciation = capped

    # 5. Apply sum insured limit
    sum_insured_cap = ZERO

    capped = min(after_depreciation, data.sum_insured)
    sum_insured_cap = money(after_depreciation - capped)
    after_depreciation = capped

    # 6. Apply deductible
    deductible = money(
        min(after_depreciation, data.deductible)
    )

    after_deductible = max(
        ZERO,
        after_depreciation - deductible,
    )

    # 7. Apply coinsurance
    coinsurance = money(
        after_deductible * data.coinsurance_pct / HUNDRED
    )

    # 8. Final payable
    payable = money(
        max(
            ZERO,
            after_deductible - coinsurance,
        )
    )

    return SettlementResult(
        claimed=claimed,
        inadmissible=inadmissible,
        depreciation=depreciation,
        deductible=deductible,
        coinsurance=coinsurance,
        sub_limit_cap=sub_limit_cap,
        sum_insured_cap=sum_insured_cap,
        payable=payable,
    )
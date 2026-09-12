from decimal import Decimal

from libs.claim_domain.models import ClaimLine, SettlementInput
from libs.claim_domain.settlement import calculate_settlement


def test_basic_settlement():
    data = SettlementInput(
        lines=(
            ClaimLine("Repair", Decimal("10000")),
        ),
        sum_insured=Decimal("50000"),
        deductible=Decimal("1000"),
    )

    result = calculate_settlement(data)

    assert result.claimed == Decimal("10000.00")
    assert result.payable == Decimal("9000.00")


def test_inadmissible_amount_is_removed_first():
    data = SettlementInput(
        lines=(
            ClaimLine("Repair", Decimal("10000")),
            ClaimLine("Excluded", Decimal("2000"), admissible=False),
        ),
        sum_insured=Decimal("50000"),
        deductible=Decimal("1000"),
    )

    result = calculate_settlement(data)

    assert result.inadmissible == Decimal("2000.00")
    assert result.payable == Decimal("9000.00")


def test_order_of_operations():
    data = SettlementInput(
        lines=(
            ClaimLine("Repair", Decimal("20000")),
        ),
        sum_insured=Decimal("50000"),
        deductible=Decimal("1000"),
        depreciation_pct=Decimal("10"),
        coinsurance_pct=Decimal("20"),
    )

    result = calculate_settlement(data)

    # 20,000
    # - 10% depreciation = 18,000
    # - 1,000 deductible = 17,000
    # - 20% coinsurance = 13,600
    assert result.depreciation == Decimal("2000.00")
    assert result.deductible == Decimal("1000.00")
    assert result.coinsurance == Decimal("3400.00")
    assert result.payable == Decimal("13600.00")
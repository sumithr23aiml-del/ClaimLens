from decimal import Decimal

from libs.claim_domain.models import ClaimLine, SettlementInput
from libs.claim_domain.settlement import calculate_settlement


def test_basic_settlement():
    data = SettlementInput(
        lines=(ClaimLine("Repair", Decimal("10000")),),
        sum_insured=Decimal("20000"),
        deductible=Decimal("1000"),
    )

    result = calculate_settlement(data)

    assert result.claimed == Decimal("10000.00")
    assert result.payable == Decimal("9000.00")


def test_inadmissible_amount_removed():
    data = SettlementInput(
        lines=(
            ClaimLine("Repair", Decimal("10000")),
            ClaimLine("Excluded", Decimal("2000"), admissible=False),
        ),
        sum_insured=Decimal("20000"),
        deductible=Decimal("1000"),
    )

    result = calculate_settlement(data)

    assert result.inadmissible == Decimal("2000.00")
    assert result.payable == Decimal("9000.00")


def test_order_of_operations():
    data = SettlementInput(
        lines=(ClaimLine("Repair", Decimal("10000")),),
        sum_insured=Decimal("8000"),
        deductible=Decimal("1000"),
        depreciation_pct=Decimal("10"),
        sub_limit=Decimal("7000"),
        coinsurance_pct=Decimal("20"),
    )

    result = calculate_settlement(data)

    assert result.depreciation == Decimal("1000.00")
    assert result.sub_limit_cap == Decimal("2000.00")
    assert result.sum_insured_cap == Decimal("0.00")
    assert result.deductible == Decimal("1000.00")
    assert result.coinsurance == Decimal("1200.00")
    assert result.payable == Decimal("4800.00")
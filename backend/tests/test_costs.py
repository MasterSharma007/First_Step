from app.core.config import Settings
from app.services.risk_management.costs import estimate_round_trip_charges


def test_round_trip_charges_are_positive_and_scale_with_turnover():
    settings = Settings()
    small = estimate_round_trip_charges(entry_price=100.0, exit_price=105.0, quantity=30, settings=settings)
    large = estimate_round_trip_charges(entry_price=1000.0, exit_price=1050.0, quantity=30, settings=settings)
    assert small > 0
    assert large > small


def test_round_trip_charges_include_flat_brokerage_floor():
    settings = Settings()
    # Even a break-even round trip (no STT-relevant premium change) still
    # pays two flat brokerage legs plus GST on them.
    charges = estimate_round_trip_charges(entry_price=1.0, exit_price=1.0, quantity=1, settings=settings)
    assert charges >= settings.brokerage_per_order * 2

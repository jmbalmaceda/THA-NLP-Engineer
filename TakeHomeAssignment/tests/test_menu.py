"""Tests for menu.py — price calculation and validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from menu import calculate_price, validate_item


class TestCalculatePrice:
    def test_basic_price_no_extras(self):
        # classic_burger regular, no extras: 8.50 + 0 (regular modifier)
        price = calculate_price("classic_burger", options={"size": "regular"})
        assert price == 8.50

    def test_price_with_size_modifier(self):
        # classic_burger large: 8.50 + 2.00 = 10.50
        price = calculate_price("classic_burger", options={"size": "large"})
        assert price == 10.50

    def test_price_with_extras(self):
        # classic_burger regular + cheese (1.00) + bacon (1.50) = 11.00
        price = calculate_price(
            "classic_burger",
            options={"size": "regular"},
            extras=["cheese", "bacon"],
        )
        assert price == 11.00

    def test_price_with_quantity(self):
        # 2x classic_burger regular = 2 * 8.50 = 17.00
        price = calculate_price("classic_burger", options={"size": "regular"}, quantity=2)
        assert price == 17.00

    def test_price_negative_modifier(self):
        # margherita small: 12.00 - 2.00 = 10.00
        price = calculate_price("margherita", options={"size": "small"})
        assert price == 10.00

    def test_price_default_options_used(self):
        # classic_burger with no options specified — defaults to regular (modifier=0)
        price = calculate_price("classic_burger")
        assert price == 8.50

    def test_milkshake_large(self):
        # milkshake large: 5.50 + 2.00 = 7.50
        price = calculate_price("milkshake", options={"size": "large", "flavor": "vanilla"})
        assert price == 7.50

    def test_extras_price_accumulates(self):
        # margherita medium + extra_cheese (2.00) + olives (1.50) = 15.50
        price = calculate_price(
            "margherita",
            options={"size": "medium"},
            extras=["extra_cheese", "olives"],
        )
        assert price == 15.50


class TestValidateItem:
    def test_valid_item_all_options_provided(self):
        ok, errors = validate_item(
            "classic_burger",
            options={"size": "regular", "patty": "beef"},
            extras=["cheese"],
        )
        assert ok is True
        assert errors == []

    def test_valid_item_optional_option_omitted(self):
        # patty is optional with a default — omitting it is fine
        ok, errors = validate_item("classic_burger", options={"size": "regular"})
        assert ok is True
        assert errors == []

    def test_missing_required_option_with_no_default(self):
        # milkshake flavor is required with no default
        ok, errors = validate_item("milkshake", options={"size": "regular"})
        assert ok is False
        assert any("flavor" in e for e in errors)

    def test_missing_required_option_that_has_default(self):
        # size is required but has a default — should be valid
        ok, errors = validate_item("classic_burger", options={})
        assert ok is True

    def test_invalid_option_value(self):
        ok, errors = validate_item("classic_burger", options={"size": "extra_large"})
        assert ok is False
        assert any("size" in e for e in errors)

    def test_invalid_extra(self):
        ok, errors = validate_item(
            "classic_burger",
            options={"size": "regular"},
            extras=["ketchup"],
        )
        assert ok is False
        assert any("ketchup" in e for e in errors)

    def test_unknown_item(self):
        ok, errors = validate_item("mystery_item")
        assert ok is False
        assert any("mystery_item" in e for e in errors)

    def test_valid_item_with_extras(self):
        ok, errors = validate_item(
            "fries",
            options={"size": "large"},
            extras=["truffle_oil", "parmesan"],
        )
        assert ok is True
        assert errors == []

    def test_multiple_errors_reported(self):
        # Invalid size AND invalid extra
        ok, errors = validate_item(
            "classic_burger",
            options={"size": "giant"},
            extras=["gold_flakes"],
        )
        assert ok is False
        assert len(errors) >= 2

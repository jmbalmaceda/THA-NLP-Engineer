"""Menu data, validation, and price calculation for the food ordering agent."""

import os
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExtraSpec:
    id: str
    price: float


@dataclass
class OptionSpec:
    type: str  # "single_choice"
    required: bool
    choices: list[str]
    default: str | None = None
    price_modifier: dict[str, float] = field(default_factory=dict)


@dataclass
class MenuItem:
    id: str
    name: str
    base_price: float
    options: dict[str, OptionSpec] = field(default_factory=dict)
    extras: list[ExtraSpec] = field(default_factory=list)


class MenuProvider(Protocol):
    def load(self) -> dict[str, MenuItem]:
        ...


class StaticMenuProvider:
    """Returns the hardcoded menu defined in this module."""

    def load(self) -> dict[str, MenuItem]:
        return _STATIC_MENU


def get_menu_provider(source: str | None = None) -> MenuProvider:
    """Factory that returns the appropriate MenuProvider based on MENU_SOURCE env var.

    Supported values: 'static' (default), 'mongodb'.
    """
    source = source or os.getenv("MENU_SOURCE", "static")
    if source == "mongodb":
        from menu_mongodb import MongoDBMenuProvider  # lazy import — only when needed
        return MongoDBMenuProvider()
    return StaticMenuProvider()


_STATIC_MENU: dict[str, MenuItem] = {
    "classic_burger": MenuItem(
        id="classic_burger",
        name="Classic Burger",
        base_price=8.50,
        options={
            "size": OptionSpec(
                type="single_choice",
                required=True,
                choices=["regular", "large"],
                default="regular",
                price_modifier={"regular": 0.0, "large": 2.00},
            ),
            "patty": OptionSpec(
                type="single_choice",
                required=False,
                choices=["beef", "chicken", "veggie"],
                default="beef",
            ),
        },
        extras=[
            ExtraSpec(id="cheese", price=1.00),
            ExtraSpec(id="bacon", price=1.50),
            ExtraSpec(id="avocado", price=2.00),
            ExtraSpec(id="extra_patty", price=3.00),
        ],
    ),
    "spicy_burger": MenuItem(
        id="spicy_burger",
        name="Spicy Jalapeño Burger",
        base_price=9.50,
        options={
            "size": OptionSpec(
                type="single_choice",
                required=True,
                choices=["regular", "large"],
                default="regular",
                price_modifier={"regular": 0.0, "large": 2.00},
            ),
            "spice_level": OptionSpec(
                type="single_choice",
                required=False,
                choices=["mild", "medium", "hot", "extra_hot"],
                default="medium",
            ),
        },
        extras=[
            ExtraSpec(id="cheese", price=1.00),
            ExtraSpec(id="bacon", price=1.50),
            ExtraSpec(id="jalapeños", price=0.75),
        ],
    ),
    "margherita": MenuItem(
        id="margherita",
        name="Margherita Pizza",
        base_price=12.00,
        options={
            "size": OptionSpec(
                type="single_choice",
                required=True,
                choices=["small", "medium", "large"],
                default="medium",
                price_modifier={"small": -2.00, "medium": 0.0, "large": 4.00},
            ),
            "crust": OptionSpec(
                type="single_choice",
                required=False,
                choices=["thin", "regular", "thick"],
                default="regular",
            ),
        },
        extras=[
            ExtraSpec(id="extra_cheese", price=2.00),
            ExtraSpec(id="olives", price=1.50),
            ExtraSpec(id="mushrooms", price=1.50),
            ExtraSpec(id="pepperoni", price=2.00),
        ],
    ),
    "fries": MenuItem(
        id="fries",
        name="French Fries",
        base_price=3.50,
        options={
            "size": OptionSpec(
                type="single_choice",
                required=True,
                choices=["small", "medium", "large"],
                default="medium",
                price_modifier={"small": -1.00, "medium": 0.0, "large": 1.50},
            ),
        },
        extras=[
            ExtraSpec(id="truffle_oil", price=2.00),
            ExtraSpec(id="parmesan", price=1.00),
            ExtraSpec(id="cheese_sauce", price=1.50),
        ],
    ),
    "onion_rings": MenuItem(
        id="onion_rings",
        name="Onion Rings",
        base_price=4.50,
        options={
            "size": OptionSpec(
                type="single_choice",
                required=True,
                choices=["small", "medium", "large"],
                default="medium",
                price_modifier={"small": -1.00, "medium": 0.0, "large": 1.50},
            ),
        },
        extras=[
            ExtraSpec(id="ranch_dip", price=0.75),
            ExtraSpec(id="spicy_mayo", price=0.75),
        ],
    ),
    "soda": MenuItem(
        id="soda",
        name="Soft Drink",
        base_price=2.00,
        options={
            "size": OptionSpec(
                type="single_choice",
                required=True,
                choices=["small", "medium", "large"],
                default="medium",
                price_modifier={"small": -0.50, "medium": 0.0, "large": 0.75},
            ),
            "flavor": OptionSpec(
                type="single_choice",
                required=True,
                choices=["cola", "diet_cola", "lemon_lime", "orange"],
                default="cola",
            ),
        },
        extras=[],
    ),
    "milkshake": MenuItem(
        id="milkshake",
        name="Milkshake",
        base_price=5.50,
        options={
            "size": OptionSpec(
                type="single_choice",
                required=True,
                choices=["regular", "large"],
                default="regular",
                price_modifier={"regular": 0.0, "large": 2.00},
            ),
            "flavor": OptionSpec(
                type="single_choice",
                required=True,
                choices=["vanilla", "chocolate", "strawberry", "oreo"],
                default=None,
            ),
        },
        extras=[
            ExtraSpec(id="whipped_cream", price=0.50),
            ExtraSpec(id="cherry_on_top", price=0.25),
        ],
    ),
}

# Populated once at import time from the configured provider.
MENU: dict[str, MenuItem] = get_menu_provider().load()


def calculate_price(
    item_id: str,
    options: dict[str, str] | None = None,
    extras: list[str] | None = None,
    quantity: int = 1,
) -> float:
    """Calculate total price for an item with given options and extras."""
    item = MENU[item_id]
    options = options or {}
    extras = extras or []

    price = item.base_price

    # Apply option price modifiers
    for opt_name, opt_spec in item.options.items():
        chosen = options.get(opt_name, opt_spec.default)
        if chosen is not None and opt_spec.price_modifier:
            price += opt_spec.price_modifier.get(chosen, 0.0)

    # Apply extras
    extras_by_id = {e.id: e for e in item.extras}
    for extra_id in extras:
        if extra_id in extras_by_id:
            price += extras_by_id[extra_id].price

    return round(price * quantity, 2)


def validate_item(
    item_id: str,
    options: dict[str, str] | None = None,
    extras: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Validate an item against the menu schema.

    Returns (is_valid, list_of_error_messages).
    """
    errors: list[str] = []
    options = options or {}
    extras = extras or []

    if item_id not in MENU:
        return False, [f"Unknown item: '{item_id}'. Available items: {', '.join(MENU.keys())}"]

    item = MENU[item_id]

    # Validate options
    for opt_name, opt_spec in item.options.items():
        chosen = options.get(opt_name)
        if chosen is None:
            # Use default if available; if required and no default, it's an error
            if opt_spec.required and opt_spec.default is None:
                errors.append(f"Required option '{opt_name}' for {item.name} is missing.")
        else:
            if chosen not in opt_spec.choices:
                errors.append(
                    f"Invalid value '{chosen}' for option '{opt_name}' on {item.name}. "
                    f"Valid choices: {', '.join(opt_spec.choices)}"
                )

    # Validate extras
    valid_extra_ids = {e.id for e in item.extras}
    for extra_id in extras:
        if extra_id not in valid_extra_ids:
            errors.append(
                f"Unknown extra '{extra_id}' for {item.name}. "
                f"Valid extras: {', '.join(valid_extra_ids) or 'none'}"
            )

    return len(errors) == 0, errors


def render_menu_text() -> str:
    """Return a human-readable menu string for the system prompt."""
    lines = ["=== MENU ===\n"]

    categories = {
        "Burgers": ["classic_burger", "spicy_burger"],
        "Pizzas": ["margherita"],
        "Sides": ["fries", "onion_rings"],
        "Drinks": ["soda", "milkshake"],
    }

    for category, item_ids in categories.items():
        lines.append(f"--- {category} ---")
        for item_id in item_ids:
            item = MENU[item_id]
            lines.append(f"\n[{item_id}] {item.name} — base price: ${item.base_price:.2f}")

            if item.options:
                lines.append("  Options:")
                for opt_name, opt_spec in item.options.items():
                    req = "required" if opt_spec.required else "optional"
                    default_str = f", default: {opt_spec.default}" if opt_spec.default else ""
                    choices_str = ", ".join(opt_spec.choices)
                    lines.append(f"    {opt_name} ({req}{default_str}): {choices_str}")
                    if opt_spec.price_modifier:
                        mods = ", ".join(
                            f"{k}: +${v:.2f}" if v >= 0 else f"{k}: -${abs(v):.2f}"
                            for k, v in opt_spec.price_modifier.items()
                            if v != 0
                        )
                        if mods:
                            lines.append(f"      price modifiers: {mods}")

            if item.extras:
                lines.append("  Extras (optional, multi-select):")
                for extra in item.extras:
                    lines.append(f"    {extra.id}: +${extra.price:.2f}")

        lines.append("")

    return "\n".join(lines)

from pathlib import Path
import json
import re


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ORDERS_FILE = PROJECT_ROOT / "data" / "orders.json"


# --------------------------------------------------
# Load orders
# --------------------------------------------------

def load_orders():

    with open(ORDERS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    # The supplied file may contain either a list
    # directly or a dictionary containing orders.
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if "orders" in data:
            return data["orders"]

    raise ValueError("Unexpected orders.json format")


# --------------------------------------------------
# Normalize order ID
# --------------------------------------------------

def normalize_order_id(order_id):

    if not isinstance(order_id, str):
        return None

    # Remove surrounding whitespace
    # and make the ID case-insensitive.
    order_id = order_id.strip().upper()

    # Expected format: ORD-1234
    if not re.fullmatch(r"ORD-\d+", order_id):
        return None

    return order_id


# --------------------------------------------------
# Sanitize order information
# --------------------------------------------------

def sanitize_order(order):

    if not order:
        return None

    # Only expose customer-safe fields.
    # Internal fields such as email, address,
    # internal notes and risk scores are excluded.
    safe_fields = {
        "order_id",
        "status",
        "carrier",
        "estimated_delivery",
        "delivery_date"
    }

    return {
        key: value
        for key, value in order.items()
        if key in safe_fields and value is not None
    }


# --------------------------------------------------
# Order lookup
# --------------------------------------------------

def lookup_order(order_id):

    # Normalize and validate the supplied order ID.
    normalized_id = normalize_order_id(order_id)

    if normalized_id is None:

        return {
            "success": False,
            "error": "invalid_order_id"
        }

    # Load the supplied mock order data.
    orders = load_orders()

    # Search for the requested order.
    for order in orders:

        stored_order_id = str(
            order.get("order_id", "")
        ).strip().upper()

        if stored_order_id == normalized_id:

            safe_order = sanitize_order(order)

            # Protect against malformed order records.
            if safe_order is None:

                return {
                    "success": False,
                    "error": "invalid_order_data"
                }

            status = str(
                safe_order.get("status", "")
            ).lower()

            # Do not expose stale delivery information
            # for cancelled or returned orders.
            if status in {"cancelled", "returned"}:

                safe_order.pop(
                    "estimated_delivery",
                    None
                )

                safe_order.pop(
                    "delivery_date",
                    None
                )

            return {
                "success": True,
                "order": safe_order
            }

    # Order ID was valid but does not exist.
    return {
        "success": False,
        "error": "order_not_found"
    }


# --------------------------------------------------
# Manual test
# --------------------------------------------------

if __name__ == "__main__":

    print("Order lookup test")
    print("-" * 50)

    test_ids = [
        "ORD-1007",
        "ord-1007",
        "  ORD-1007  ",
        "INVALID",
        "ORD-999999"
    ]

    for order_id in test_ids:

        print()
        print("Input:", repr(order_id))

        result = lookup_order(order_id)

        print("Result:", result)
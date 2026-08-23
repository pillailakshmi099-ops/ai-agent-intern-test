from app.order_tool import lookup_order


# --------------------------------------------------
# Basic lookup
# --------------------------------------------------

def test_valid_order_lookup():

    result = lookup_order("ORD-1007")

    assert result["success"] is True
    assert result["order"]["order_id"] == "ORD-1007"
    assert result["order"]["status"] == "shipped"
    assert result["order"]["estimated_delivery"] == "2026-08-22"


# --------------------------------------------------
# Order ID normalization
# --------------------------------------------------

def test_order_id_normalization():

    lowercase_result = lookup_order("ord-1007")
    whitespace_result = lookup_order("  ORD-1007  ")

    assert lowercase_result["success"] is True
    assert whitespace_result["success"] is True

    assert (
        lowercase_result["order"]["order_id"]
        == "ORD-1007"
    )

    assert (
        whitespace_result["order"]["order_id"]
        == "ORD-1007"
    )


# --------------------------------------------------
# Invalid order ID
# --------------------------------------------------

def test_invalid_order_id():

    result = lookup_order("INVALID")

    assert result["success"] is False
    assert result["error"] == "invalid_order_id"


# --------------------------------------------------
# Unknown order
# --------------------------------------------------

def test_unknown_order():

    result = lookup_order("ORD-999999")

    assert result["success"] is False
    assert result["error"] == "order_not_found"


# --------------------------------------------------
# Cancelled order must not expose stale ETA
# --------------------------------------------------

def test_cancelled_order_has_no_eta():

    result = lookup_order("ORD-1004")

    assert result["success"] is True
    assert result["order"]["status"] == "cancelled"

    assert "estimated_delivery" not in result["order"]
    assert "delivery_date" not in result["order"]


# --------------------------------------------------
# Returned order must not expose stale ETA
# --------------------------------------------------

def test_returned_order_has_no_eta():

    result = lookup_order("ORD-1008")

    assert result["success"] is True
    assert result["order"]["status"] == "returned"

    assert "estimated_delivery" not in result["order"]
    assert "delivery_date" not in result["order"]


# --------------------------------------------------
# Shipped order without ETA
# --------------------------------------------------

def test_shipped_order_without_eta():

    result = lookup_order("ORD-1011")

    assert result["success"] is True
    assert result["order"]["status"] == "shipped"

    # The system must not invent an ETA.
    assert "estimated_delivery" not in result["order"]
    assert "delivery_date" not in result["order"]


# --------------------------------------------------
# Privacy protection
# --------------------------------------------------

def test_internal_fields_are_not_exposed():

    result = lookup_order("ORD-1007")

    assert result["success"] is True

    order = result["order"]

    forbidden_fields = {
        "email",
        "customer_email",
        "address",
        "customer_address",
        "internal_notes",
        "risk_score"
    }

    for field in forbidden_fields:

        assert field not in order
import os
import pytest
from unittest.mock import patch, MagicMock
from backend.app import create_app
from backend.app.utils import (
    ResourceNotFoundError,
    PaymentVerificationError,
    PaymentGatewayError,
)

@pytest.fixture
def client():
    app = create_app({"TESTING": True, "PAYMENTS_ENABLED": True})
    app.config["RAZORPAY_KEY_ID"] = os.getenv("RAZORPAY_KEY_ID", "rzp_test_example")
    app.config["RAZORPAY_KEY_SECRET"] = os.getenv("RAZORPAY_KEY_SECRET", "mock_key_secret_for_unit_tests")
    with app.test_client() as c:
        yield c

def test_create_order_missing_booking_reference_and_token(client):
    """
    BUG-06 guard verification:
    Arbitrary client payload or missing bookingReference/token must be rejected.
    """
    res = client.post("/api/create-order", json={})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "MISSING_FIELDS"

def test_create_order_rejects_client_supplied_amount_without_booking(client):
    """
    BUG-06: Direct attempt to pass client price without booking reference is rejected.
    """
    res = client.post("/api/create-order", json={"amount": 99, "currency": "INR"})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "MISSING_FIELDS"

def test_create_order_missing_token_only(client):
    res = client.post("/api/create-order", json={"bookingReference": "JBX-2026-TEST01"})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "MISSING_FIELDS"

def test_create_order_booking_not_found(client):
    with patch("backend.app.routes.payment_routes.get_payment_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.create_order.side_effect = ResourceNotFoundError("Booking reference 'JBX-404' not found.")
        mock_get_svc.return_value = mock_svc

        res = client.post("/api/create-order", json={
            "bookingReference": "JBX-404",
            "token": "tok_nonexistent"
        })
        assert res.status_code == 404
        json_data = res.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "NOT_FOUND"

def test_create_order_success_uses_server_calculated_pricing(client):
    """
    Verifies order creation succeeds and strictly uses server-calculated pricing,
    ignoring any client-injected amount.
    """
    mock_order_res = {
        "orderId": "order_mock12345",
        "bookingReference": "JBX-2026-0001",
        "amountMinor": 50000,
        "amountRupees": 500.0,
        "currency": "INR",
        "keyId": os.getenv("RAZORPAY_KEY_ID", "rzp_test_example"),
        "customer": {"name": "Test User", "phone": "9876543210"}
    }
    with patch("backend.app.routes.payment_routes.get_payment_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.create_order.return_value = mock_order_res
        mock_get_svc.return_value = mock_svc

        res = client.post("/api/create-order", json={
            "bookingReference": "JBX-2026-0001",
            "token": "valid_token_32_chars",
            "amount": 99 # Injected client attempt should be ignored
        })
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["order_id"] == "order_mock12345"
        assert json_data["amount"] == 50000
        assert json_data["currency"] == "INR"
        assert json_data["key_id"] == os.getenv("RAZORPAY_KEY_ID", "rzp_test_example")
        mock_svc.create_order.assert_called_once_with("JBX-2026-0001", "valid_token_32_chars", idempotency_key=None)

def test_create_order_gateway_error(client):
    with patch("backend.app.routes.payment_routes.get_payment_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.create_order.side_effect = PaymentGatewayError("Razorpay gateway timeout")
        mock_get_svc.return_value = mock_svc

        res = client.post("/api/create-order", json={
            "bookingReference": "JBX-2026-0001",
            "token": "valid_token_32_chars"
        })
        assert res.status_code == 502
        json_data = res.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "PAYMENT_GATEWAY_ERROR"

def test_verify_payment_missing_fields(client):
    # Missing signature, bookingReference, token
    res = client.post("/api/verify-payment", json={
        "razorpay_order_id": "order_123",
        "razorpay_payment_id": "pay_123"
    })
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "MISSING_FIELDS"

def test_verify_payment_signature_mismatch(client):
    with patch("backend.app.routes.payment_routes.get_payment_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.verify_payment.side_effect = PaymentVerificationError("Cryptographic payment signature verification failed.")
        mock_get_svc.return_value = mock_svc

        res = client.post("/api/verify-payment", json={
            "bookingReference": "JBX-2026-0001",
            "token": "valid_token_32_chars",
            "razorpay_order_id": "order_test_123",
            "razorpay_payment_id": "pay_test_456",
            "razorpay_signature": "tampered_signature_hex"
        })
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "PAYMENT_VERIFICATION_FAILED"

def test_verify_payment_success_with_hmac(client):
    with patch("backend.app.routes.payment_routes.get_payment_service") as mock_get_svc:
        mock_svc = MagicMock()
        order_id = "order_valid_789"
        payment_id = "pay_valid_101"
        mock_svc.verify_payment.return_value = {
            "bookingReference": "JBX-2026-0001",
            "bookingStatus": "confirmed",
            "paymentStatus": "paid",
            "orderId": order_id,
            "paymentId": payment_id,
            "amountMinor": 50000,
            "currency": "INR",
            "message": "Payment verified and booking confirmed successfully."
        }
        mock_get_svc.return_value = mock_svc

        res = client.post("/api/verify-payment", json={
            "bookingReference": "JBX-2026-0001",
            "token": "valid_token_32_chars",
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": "valid_hmac_hex"
        })
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["paymentStatus"] == "paid"
        assert json_data["data"]["orderId"] == order_id
        assert json_data["data"]["paymentId"] == payment_id

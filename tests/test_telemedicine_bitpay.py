import requests

def bitpay_request_payment(self, api_key, redirect_url, amount, order_id):
    data = {
        'api': api_key,
        'redirect': redirect_url,
        'amount': amount,
        'factorId': order_id,
    }

    response = requests.post('https://bitpay.ir/payment/gateway-send', data=data)

    if response.ok:
        return response
    else:
        return {'status': -1, 'message': 'Failed to connect to the payment gateway.'}

# -----------------------------
# Unit tests for bitpay_request_payment
# Framework: pytest
# Mocking: unittest.mock.patch for requests.post
# -----------------------------

from unittest.mock import patch, Mock
import pytest

BITPAY_URL = 'https://bitpay.ir/payment/gateway-send'


def _call(data_overrides=None, self_obj=None):
    """
    Helper to build inputs and expected payload for the function under test.
    Returns (args, expected_data_dict)
    """
    base = {
        'api_key': 'test_api_key_123',
        'redirect_url': 'https://example.com/return?param=ä&z=1',
        'amount': 123450,  # integer amount as given
        'order_id': 'ORDER-XYZ-001',
    }
    if data_overrides:
        base.update(data_overrides)
    expected_data = {
        'api': base['api_key'],
        'redirect': base['redirect_url'],
        'amount': base['amount'],
        'factorId': base['order_id'],
    }
    args = (self_obj, base['api_key'], base['redirect_url'], base['amount'], base['order_id'])
    return args, expected_data


@patch("requests.post")
def test_bitpay_request_payment_happy_path_returns_response_and_uses_correct_payload(mock_post):
    # Arrange
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": 1, "trackId": "T-12345"}
    mock_post.return_value = mock_response

    args, expected_data = _call()

    # Act
    returned = bitpay_request_payment(*args)

    # Assert
    assert returned is mock_response, "Should return the successful Response object"
    mock_post.assert_called_once()
    called_url, = mock_post.call_args[0]
    called_kwargs = mock_post.call_args[1]
    assert called_url == BITPAY_URL, "Should call BitPay gateway send endpoint"
    assert 'data' in called_kwargs, "Should pass request data in 'data' kwarg"
    assert called_kwargs['data'] == expected_data, "Should map all fields correctly to BitPay payload"


@patch("requests.post")
def test_bitpay_request_payment_failure_returns_error_dict(mock_post):
    # Arrange
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 502
    mock_post.return_value = mock_response

    args, expected_data = _call()

    # Act
    returned = bitpay_request_payment(*args)

    # Assert
    assert isinstance(returned, dict), "On failure, function should return a dict error"
    assert returned == {'status': -1, 'message': 'Failed to connect to the payment gateway.'}
    mock_post.assert_called_once_with(BITPAY_URL, data=expected_data)


@patch("requests.post")
def test_bitpay_request_payment_with_zero_amount(mock_post):
    # Arrange
    mock_response = Mock()
    mock_response.ok = True
    mock_post.return_value = mock_response

    args, expected_data = _call({'amount': 0})

    # Act
    returned = bitpay_request_payment(*args)

    # Assert
    assert returned is mock_response
    mock_post.assert_called_once_with(BITPAY_URL, data=expected_data)


@patch("requests.post")
def test_bitpay_request_payment_with_negative_amount(mock_post):
    # Arrange
    mock_response = Mock()
    mock_response.ok = True
    mock_post.return_value = mock_response

    args, expected_data = _call({'amount': -100})

    # Act
    returned = bitpay_request_payment(*args)

    # Assert
    assert returned is mock_response
    mock_post.assert_called_once_with(BITPAY_URL, data=expected_data)


@patch("requests.post")
def test_bitpay_request_payment_special_chars_in_redirect_and_order_id(mock_post):
    # Arrange
    mock_response = Mock()
    mock_response.ok = True
    mock_post.return_value = mock_response

    overrides = {
        'redirect_url': 'https://example.com/callback?query=سلام&emoji=😀',
        'order_id': 'ORD-ç∆✓-٩٩',
    }
    args, expected_data = _call(overrides)

    # Act
    returned = bitpay_request_payment(*args)

    # Assert
    assert returned is mock_response
    mock_post.assert_called_once_with(BITPAY_URL, data=expected_data)


def test_bitpay_request_payment_propagates_exceptions_on_post_failure(monkeypatch):
    # Arrange
    class FakeError(Exception):
        pass

    def _boom(*_a, **_kw):
        raise FakeError("network down")

    monkeypatch.setattr("requests.post", _boom)

    args, _ = _call()

    # Act / Assert
    with pytest.raises(FakeError):
        bitpay_request_payment(*args)


@patch("requests.post")
def test_bitpay_request_payment_self_parameter_is_ignored(mock_post):
    # Arrange
    mock_response = Mock()
    mock_response.ok = True
    mock_post.return_value = mock_response

    # Supply a non-None self to verify it does not affect behavior
    class DummySelf:
        pass

    self_obj = DummySelf()
    args, expected_data = _call(self_obj=self_obj)

    # Act
    returned = bitpay_request_payment(*args)

    # Assert
    assert returned is mock_response
    mock_post.assert_called_once_with(BITPAY_URL, data=expected_data)
import requests


def bitpay_request_payment(self, api_key, redirect_url, amount, order_id):
    """
    Create a BitPay payment request and return the gateway response.
    
    Sends a POST request to the BitPay gateway endpoint with the provided API key, redirect URL, amount, and order ID.
    
    Parameters:
        api_key (str): Merchant API key for the BitPay gateway.
        redirect_url (str): URL to which the user will be redirected after payment.
        amount (int|float|str): Payment amount accepted by the gateway (type accepted by the API).
        order_id (str|int): Merchant's order identifier sent as `factorId`.
    
    Returns:
        requests.Response: The HTTP response from the gateway when the request succeeds (response.ok is True).
        dict: On failure, a dict with keys `status` (-1) and `message` describing the failure.
    """
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

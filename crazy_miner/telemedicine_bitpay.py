import requests


def bitpay_request_payment(self, api_key, redirect_url, amount, order_id):
    """
    Create a BitPay payment request and return the gateway response.
    
    Sends a form-encoded POST to the BitPay gateway endpoint with the provided API key, redirect URL, amount, and order ID (sent as `factorId`). On a successful HTTP response (response.ok is True) the raw `requests.Response` is returned; on an unsuccessful HTTP response a dict `{'status': -1, 'message': 'Failed to connect to the payment gateway.'}` is returned. Network or HTTP-related exceptions from `requests.post` are not handled and will propagate.
    
    Parameters:
        api_key (str): Merchant API key for the BitPay gateway.
        redirect_url (str): URL to redirect the user after payment.
        amount (int|float|str): Payment amount as accepted by the gateway.
        order_id (str|int): Merchant order identifier; sent to the gateway as `factorId`.
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

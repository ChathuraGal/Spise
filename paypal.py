import requests
import json


def make_payment(client_id, client_secret, amount, batch_id):

    # Get an access token to make API requests
    response = requests.post(
        "https://api.sandbox.paypal.com/v1/oauth2/token",
        headers={
            "Accept": "application/json",
            "Accept-Language": "en_US",
        },
        auth=(client_id, client_secret),
        data={
            "grant_type": "client_credentials",
        }
    )

    access_token = response.json()["access_token"]

    # Make a payment using the access token
    response = requests.post(
        "https://api.sandbox.paypal.com/v1/payments/payouts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "sender_batch_header": {
                "sender_batch_id": batch_id,
                "email_subject": "You have a payout!",
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{str(amount)}",
                        "currency": "GBP",
                    },
                    "receiver": "receiver@example.com",
                    "note": "Thanks for your business!",
                    "sender_item_id": "item_id_123",
                }
            ]
        }
    )

    # Check the response to see if the payment was successful
    if response.status_code == 201:
        response_text = "Payment sent successfully!"
    else:
        response_text = f"Payment failed: {response.status_code}"

    return access_token, response_text


def make_requests(access_token):
    response = requests.get('https://api.paypal.com/v1/checkout/orders',
                           headers={
                               "Authorization": f"Bearer {access_token}",
                              "Content-Type": "application/json",
                           })
    if response.status_code != 200:
        print('Request failed with HTTP code', response.status_code)
    else:
        data = json.loads(response.text)
        print(data)

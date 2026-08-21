import requests
import base64
from datetime import datetime
import json

# Safaricom Sandbox Developer Credentials
# (Swap these out with production credentials inside a .env block later)
CONSUMER_KEY = "your_daraja_consumer_key"
CONSUMER_SECRET = "your_daraja_consumer_secret"
BUSINESS_SHORT_CODE = "174379"  # Standard Customer Paybill Sandbox code
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
CALLBACK_URL = " https://ty-postdigestive-angeles.ngrok-free.app/mpesa/callback/" # Must be an HTTPS link

def get_access_token():
    """Generates a valid bearer token from Safaricom for API operations."""
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        print(f"Token authorization failed: {e}")
    return None

def initiate_stk_push(phone_number, amount, booking_id):
    """Triggers an STK Push menu pop-up request on the customer's phone handset."""
    access_token = get_access_token()
    if not access_token:
        return None

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_string = f"{BUSINESS_SHORT_CODE}{PASSKEY}{timestamp}"
    encoded_password = base64.b64encode(password_string.encode()).decode()

    # Format numbers safely into Safaricom standard (e.g., 2547XXXXXXXX)
    if phone_number.startswith("0"):
        phone_number = "254" + phone_number[1:]
    elif phone_number.startswith("+"):
        phone_number = phone_number.replace("+", "")

    payload = {
        "BusinessShortCode": BUSINESS_SHORT_CODE,
        "Password": encoded_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount), # Cast safely to flat integer sums for test requests
        "PartyA": phone_number,
        "PartyB": BUSINESS_SHORT_CODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": f"GH-{booking_id}",
        "TransactionDesc": f"Booking Payment for reservation tracking ID {booking_id}"
    }

    try:
        res = requests.post(url, json=payload, headers=headers)
        return res.json()
    except Exception as e:
        print(f"STK trigger communication failed: {e}")
        return None
#!/usr/bin/env python3
"""
M-Pesa API Credentials Test Script

This script tests the M-Pesa API credentials by attempting to get an access token
and making a simple API request (STK Push simulation).
"""

import os
import sys
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime
import base64

# ---------------- Logging Configuration ---------------- #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------- Core Logic ---------------- #
def verify_mpesa_credentials():
    """Verify M-Pesa API credentials by getting an access token and sending STK Push"""
    
    # Load .env variables
    load_dotenv()

    consumer_key = os.getenv('MPESA_CONSUMER_KEY')
    consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
    shortcode = os.getenv('MPESA_SHORTCODE')  # Usually 174379 in sandbox
    passkey = os.getenv('MPESA_PASSKEY')
    callback_url = os.getenv('MPESA_CALLBACK_URL', 'https://your-callback-url.com/mpesa-callback')
    test_phone = os.getenv('MPESA_TEST_PHONE', '254708374149')  # Sandbox test phone

    if not all([consumer_key, consumer_secret, shortcode, passkey]):
        logger.error("Missing one or more required environment variables")
        return False

    # Step 1: Get access token
    logger.info("Requesting access token...")
    try:
        auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        r = requests.get(auth_url, auth=(consumer_key, consumer_secret))
        r.raise_for_status()
        access_token = r.json().get("access_token")

        if not access_token:
            logger.error("Failed to get access token.")
            return False

        logger.info("✅ Access token received.")
    except Exception as e:
        logger.error(f"Error retrieving token: {e}")
        return False

    # Step 2: Prepare STK Push request
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw_password = shortcode + passkey + timestamp
    encoded_password = base64.b64encode(raw_password.encode()).decode('utf-8')

    payload = {
        "BusinessShortCode": shortcode,
        "Password": encoded_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": 1,  # Test amount
        "PartyA": test_phone,
        "PartyB": shortcode,
        "PhoneNumber": test_phone,
        "CallBackURL": callback_url,
        "AccountReference": "Test123",
        "TransactionDesc": "Test payment"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Step 3: Send STK Push request
    try:
        logger.info("Sending STK Push request...")
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers
        )

        logger.info(f"STK Push status: {response.status_code}")
        response.raise_for_status()
        result = response.json()

        if result.get("ResponseCode") == "0":
            logger.info("✅ STK Push simulation successful.")
            logger.info(f"CheckoutRequestID: {result.get('CheckoutRequestID')}")
            return True
        else:
            logger.error(f"STK Push failed: {result}")
            return False

    except Exception as e:
        logger.error(f"STK Push error: {e}")
        return False

# ---------------- Entry Point ---------------- #
if __name__ == "__main__":
    print("\n" + "="*60)
    print("M-Pesa API Credentials Test")
    print("="*60)

    success = verify_mpesa_credentials()

    print("\n" + "="*60)
    print("Test Result:", "✅ SUCCESS" if success else "❌ FAILED")
    print("="*60)

    if not success:
        print("\nTroubleshooting Tips:")
        print("1. Ensure your .env file contains the correct credentials")
        print("2. Use the Safaricom sandbox test phone number: 254708374149")
        print("3. Ensure your callback URL is reachable (use ngrok)")
        print("4. Check that your app is approved in the Safaricom developer portal")

    sys.exit(0 if success else 1)

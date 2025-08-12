import logging
import sys
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import json
import base64
import os
from dotenv import load_dotenv
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class PaymentHandler:
    def __init__(self):
        # Load environment variables directly from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get credentials - matching test script approach
        self.consumer_key = os.getenv('MPESA_CONSUMER_KEY')
        self.consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
        self.mpesa_shortcode = os.getenv('MPESA_SHORTCODE')
        self.mpesa_passkey = os.getenv('MPESA_PASSKEY')
        self.test_phone = os.getenv('MPESA_TEST_PHONE', '254708374149')
        self.mpesa_callback = os.getenv('MPESA_CALLBACK_URL')
        
        # Check for simulation mode
        self.simulation_mode = os.getenv('SIMULATION_MODE', 'False').lower() in ('true', '1', 't')
        
        logger.info("\n===== M-Pesa Configuration =====")
        logger.info(f"Simulation Mode: {'ENABLED' if self.simulation_mode else 'DISABLED'}")
        
        if not self.simulation_mode:
            # Log credential status (without exposing full values)
            logger.info("\n===== M-Pesa Credentials Status =====")
            logger.info(f"Shortcode: {self.mpesa_shortcode}")
            logger.info(f"Passkey: {'*' * 8}{self.mpesa_passkey[-4:] if self.mpesa_passkey else ''}")
            logger.info(f"Consumer Key: {self.consumer_key[:5]}...{self.consumer_key[-5:] if self.consumer_key else ''}")
            logger.info(f"Consumer Secret: {'*' * 8}{self.consumer_secret[-4:] if self.consumer_secret else ''}")
            logger.info(f"Callback URL: {self.mpesa_callback}")
            logger.info(f"Test Phone: {self.test_phone}")
        
        # Generate access token
        self.access_token = None
        try:
            self.access_token = self._generate_access_token()
            logger.info("Access token generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate access token: {e}")
            raise

    def _generate_access_token(self) -> str:
        """
        Generate M-Pesa OAuth access token
        
        Returns:
            str: The access token
            
        Raises:
            ValueError: If authentication fails or response is invalid
            ConnectionError: If there's a network error
        """
        auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        
        # Validate credentials are present
        if not all([self.consumer_key, self.consumer_secret]):
            error_msg = "M-Pesa credentials are not properly configured. Check your .env file."
            logger.error(error_msg)
            logger.error(f"Consumer Key: {'Present' if self.consumer_key else 'Missing'}")
            logger.error(f"Consumer Secret: {'Present' if self.consumer_secret else 'Missing'}")
            raise ValueError(error_msg)
            
        logger.info("\n===== Generating Access Token =====")
        logger.info(f"Auth URL: {auth_url}")
        logger.info(f"Using Consumer Key: {self.consumer_key[:5]}...{self.consumer_key[-5:] if self.consumer_key else ''}")
        logger.info(f"Using Consumer Secret: {'*' * 8}{self.consumer_secret[-4:] if self.consumer_secret else ''}")
        
        # Log environment for debugging
        logger.info("\n===== Environment Details =====")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Requests Version: {requests.__version__}")
        logger.info(f"Current Time: {datetime.now().isoformat()}")
        
        try:
            # Make the request with basic auth - matching test script
            response = requests.get(
                auth_url,
                auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            logger.info(f"Auth response status: {response.status_code}")
            logger.info(f"Auth response headers: {response.headers}")
            logger.info(f"Auth response content: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if 'access_token' not in data:
                error_msg = f"Access token not found in response: {data}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            access_token = data['access_token']
            expires_in = int(data.get('expires_in', 3599))  # Convert to int and default to 1 hour if not provided
            
            # Store token expiration time (with 5-minute buffer)
            self.token_expiry = datetime.now().timestamp() + expires_in - 300
            
            logger.info(f"Successfully obtained access token: {access_token[:10]}...")
            logger.info(f"Token expires in: {expires_in} seconds")
            return access_token
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get access token: {str(e)}"
            logger.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response headers: {e.response.headers}")
                logger.error(f"Response content: {e.response.text}")
            raise ConnectionError(error_msg) from e
            
    def _is_token_valid(self) -> bool:
        """Check if the current access token is still valid"""
        if not hasattr(self, 'token_expiry') or not self.token_expiry:
            return False
        return datetime.now().timestamp() < self.token_expiry
        
    def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if necessary"""
        if not hasattr(self, 'access_token') or not self._is_token_valid():
            logger.info("Access token missing or expired, generating a new one...")
            self.access_token = self._generate_access_token()
            self.token_expiry = datetime.now().timestamp() + 3599 - 300  # Default to 1 hour if not provided
            
    def _get_timestamp(self) -> str:
        """Get current timestamp in the format required by M-Pesa"""
        return datetime.now().strftime('%Y%m%d%H%M%S')
    
    def _generate_password(self, timestamp: str) -> str:
        """
        Generate M-Pesa API password using the provided timestamp.
        The password is a base64 encoded string of (shortcode + passkey + timestamp)
        """
        password_str = f"{self.mpesa_shortcode}{self.mpesa_passkey}{timestamp}"
        password_bytes = password_str.encode('utf-8')
        password_base64 = base64.b64encode(password_bytes).decode('utf-8')

        logger.info("\n===== Password Generation Debug =====")
        logger.info(f"Shortcode: {self.mpesa_shortcode}")
        logger.info(f"Passkey: {'*' * (len(self.mpesa_passkey) - 4) + self.mpesa_passkey[-4:] if self.mpesa_passkey and len(self.mpesa_passkey) > 4 else '****'}")
        logger.info(f"Timestamp: {timestamp}")
        logger.info(f"Password (base64): {password_base64}")
        
        return password_base64
    
    def _log_credentials(self):
        """Log credential status (safely)"""
        logger.info("\n===== M-Pesa Credentials Status =====")
        logger.info(f"Shortcode: {self.mpesa_shortcode}")
        logger.info(f"Passkey: {'*' * 8}{self.mpesa_passkey[-4:] if self.mpesa_passkey else ''}")
        logger.info(f"Consumer Key: {self.consumer_key[:5]}...{self.consumer_key[-5:] if self.consumer_key else ''}")
        logger.info(f"Callback URL: {self.mpesa_callback}")
        logger.info(f"Test Phone: {self.test_phone}")
        
    def _prepare_phone_number(self, phone: str) -> str:
        """Format phone number to 2547... format"""
        phone = str(phone).strip()
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+254'):
            phone = phone[1:]
        elif phone.startswith('7') and len(phone) == 9:
            phone = '254' + phone
        return phone

    def _simulate_stk_push(self, amount: float, order_id: str, description: str, phone: str = None) -> Dict:
        """Simulate STK push for testing"""
        logger.info("\n===== SIMULATION MODE =====")
        logger.info(f"Simulating STK push for order {order_id}")
        logger.info(f"Phone: {phone or self.test_phone}")
        logger.info(f"Amount: {amount}, Description: {description}")
        logger.info("No actual payment will be processed in simulation mode")
        
        # Generate a mock response that matches the real API
        return {
            'status': 'success',
            'data': {
                'MerchantRequestID': f'sim-{order_id}-req',
                'CheckoutRequestID': f'sim-{order_id}-chk',
                'ResponseCode': '0',
                'ResponseDescription': 'Success. Request accepted for processing',
                'CustomerMessage': 'Success. Request accepted for processing'
            },
            'message': '✅ *Payment Simulation Successful*\n\n'
                     f'Order ID: {order_id}\n'
                     f'Amount: KES {amount:,.2f}\n\n'
                     'ℹ️ *This is a simulation* - No actual payment was processed.\n'
                     'In production, the customer would receive an M-Pesa STK push.',
            'checkout_request_id': f'sim-{order_id}-chk',
            'merchant_request_id': f'sim-{order_id}-req',
            'simulation': True,
            'simulation_note': 'This is a test transaction. No money was transferred.'
        }
        
    def initiate_stk_push(self, amount: float, order_id: str, description: str, phone: str = None) -> Dict:
        """
        Initiate M-Pesa STK push payment request.
        
        Args:
            amount: Amount to charge (KES)
            order_id: Unique order ID for reference
            description: Description of the payment (max 20 chars)
            phone: Optional phone number (defaults to test number from .env)
            
        Returns:
            Dictionary containing the API response or error details
            
        Raises:
            ValueError: If the request is invalid
            ConnectionError: If there's a network error
            Exception: For other unexpected errors
        """
        # Check if we're in simulation mode
        if self.simulation_mode:
            return self._simulate_stk_push(amount, order_id, description, phone)
            
        try:
            # Log credentials status
            self._log_credentials()
            
            # Ensure we have a valid access token
            self._ensure_valid_token()
            
            logger.info("\n===== Initiating STK Push =====")
            logger.info(f"Order ID: {order_id}")
            logger.info(f"Amount: {amount}")
            logger.info(f"Description: {description}")
            
            # Use test phone number if none provided and format it
            phone = self._prepare_phone_number(phone or self.test_phone)
            logger.info(f"Using phone number: {phone}")
            
            # Log the complete request details
            logger.info("\n===== STK Push Request Details =====")
            logger.info(f"URL: https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest")
            logger.info(f"Headers: {json.dumps(headers, indent=2)}")
            
            # Create a safe copy of the payload for logging (without password)
            log_payload = payload.copy()
            log_payload['Password'] = '********'  # Mask password in logs
            logger.info(f"Request Payload: {json.dumps(log_payload, indent=2)}")
            
            # Log the actual password being sent (for debugging)
            logger.info(f"Password being sent (first 20 chars): {password[:20]}...")
            
            # Log the raw password generation details for debugging
            password_str = f"{self.mpesa_shortcode}{self.mpesa_passkey}{timestamp}"
            logger.info("\n===== Password Generation Debug =====")
            logger.info(f"Raw String: {password_str}")
            logger.info(f"String Length: {len(password_str)}")
            logger.info(f"Base64 Encoded: {password}")
            logger.info(f"Base64 Decoded: {base64.b64decode(password).decode('utf-8')}")
            
            # Make the actual API request
            try:
                logger.info("\nSending STK Push request...")
                response = requests.post(
                    "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                # Log response details
                logger.info(f"STK Push response status: {response.status_code}")
                logger.info(f"STK Push response headers: {response.headers}")
                logger.info(f"STK Push response text: {response.text}")
            
                response_data = response.json()
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response")
                return {
                    'status': 'error',
                    'message': 'Invalid response from M-Pesa',
                    'details': 'Failed to parse JSON response',
                    'status_code': response.status_code,
                    'raw_response': response.text
                }
                
            # Check for HTTP errors
            response.raise_for_status()
                
            # Check for M-Pesa API errors
            if 'errorCode' in response_data:
                error_code = response_data.get('errorCode', 'UNKNOWN')
                error_msg = response_data.get('errorMessage', 'Unknown error')
                logger.error(f"M-Pesa API Error: {error_msg} (Code: {error_code})")
                    
                return {
                    'status': 'error',
                    'message': 'Payment processing failed',
                    'details': f"{error_msg} (Code: {error_code})",
                    'status_code': response.status_code,
                    'error_code': error_code
                }
                
            # Successful response
            logger.info("STK Push initiated successfully")
            return {
                'status': 'success',
                'data': response_data,
                'message': 'Payment request sent successfully',
                'checkout_request_id': response_data.get('CheckoutRequestID'),
                'merchant_request_id': response_data.get('MerchantRequestID')
            }
                
        except requests.exceptions.HTTPError as http_err:
            error_msg = f"HTTP error occurred: {http_err}"
            logger.error(error_msg)
                
            # Try to extract more details from the error response
            error_details = str(http_err)
            status_code = 500
            
            if hasattr(http_err, 'response') and http_err.response is not None:
                try:
                    error_data = http_err.response.json()
                    error_details = json.dumps(error_data, indent=2)
                    status_code = http_err.response.status_code
                except Exception as e:
                    error_details = http_err.response.text or str(e)
                    status_code = getattr(http_err.response, 'status_code', 500)
            
            return {
                'status': 'error',
                'message': 'Payment processing failed',
                'details': error_details,
                'status_code': status_code
            }
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'error': 'An unexpected error occurred while processing your payment.',
                'details': str(e)
            }

    def generate_receipt(self, order_details: Dict) -> str:
        """Generate receipt for successful order"""
        receipt_id = f"RCPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        receipt_content = {
            "receipt_id": receipt_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "customer": order_details.get('customer_phone'),
            "items": order_details['items'],
            "subtotal": sum(item['total'] for item in order_details['items']),
            "delivery_fee": order_details.get('delivery_fee', 0),
            "total": sum(item['total'] for item in order_details['items']) + order_details.get('delivery_fee', 0),
            "payment_method": "M-Pesa",
            "payment_status": "completed",
            "delivery_option": order_details.get('delivery_option', 'pickup'),
            "shop_info": self._load_shop_info()
        }
        
        # Save receipt to file
        receipt_path = f"receipts/generated_receipts/{receipt_id}.json"
        with open(receipt_path, 'w') as f:
            json.dump(receipt_content, f, indent=2)
        
        return receipt_path

    def _load_shop_info(self) -> Dict:
        """Load shop information from JSON file"""
        try:
            with open('data/shop_info.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"error": "Shop information not found"}
    
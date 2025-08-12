from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any
import hmac
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for demo purposes
# In production, use a proper database
payment_status = {}

@router.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    """
    Handle M-Pesa STK Push callback from Safaricom
    """
    try:
        # Parse the callback data
        callback_data = await request.json()
        logger.info(f"Received M-Pesa callback: {json.dumps(callback_data, indent=2)}")
        
        # Extract the important parts of the callback
        result = callback_data.get('Body', {}).get('stkCallback', {})
        result_code = result.get('ResultCode')
        result_desc = result.get('ResultDesc')
        checkout_request_id = result.get('CheckoutRequestID')
        merchant_request_id = result.get('MerchantRequestID')
        
        # Log the full result for debugging
        logger.info(f"Processing callback - RequestID: {merchant_request_id}, CheckoutID: {checkout_request_id}")
        logger.info(f"ResultCode: {result_code}, Description: {result_desc}")
        
        # Process the callback based on result code
        if result_code == 0:
            # Payment was successful
            metadata = {}
            for item in result.get('CallbackMetadata', {}).get('Item', []):
                if 'Name' in item and 'Value' in item:
                    metadata[item['Name']] = item['Value']
            
            # Extract transaction details
            transaction_id = metadata.get('MpesaReceiptNumber')
            phone = metadata.get('PhoneNumber')
            amount = metadata.get('Amount')
            
            # Log the successful transaction
            logger.info(f"Payment successful - TransactionID: {transaction_id}, Phone: {phone}, Amount: {amount}")
            
            # Store the successful payment
            payment_status[checkout_request_id] = {
                'status': 'completed',
                'transaction_id': transaction_id,
                'phone': phone,
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata
            }
            
            # Send success response
            response = {
                'status': 'success',
                'message': 'Callback processed successfully',
                'checkout_request_id': checkout_request_id,
                'transaction_id': transaction_id,
                'amount': amount,
                'phone': phone
            }
            logger.info(f"Sending success response: {response}")
            return response
            
        elif result_code == 1037:  # DS timeout user cannot be reached
            logger.warning(f"M-Pesa STK Push timeout - User not reachable: {result_desc}")
            payment_status[checkout_request_id] = {
                'status': 'failed',
                'error_code': result_code,
                'error_message': 'Payment timeout - Could not reach your phone. Please ensure your phone is on and has network coverage.',
                'retry_possible': True
            }
        else:
            # Other payment failures
            logger.warning(f"Payment failed: {result_code} - {result_desc}")
            payment_status[checkout_request_id] = {
                'status': 'failed',
                'error_code': result_code,
                'error_message': result_desc,
                'retry_possible': result_code in [1, 1037]  # Some errors can be retried
            }
        
        # For failed payments, log and return appropriate response
        return {
            'status': 'error',
            'message': 'Payment processing failed',
            'error_code': result_code,
            'error_message': payment_status[checkout_request_id]['error_message'],
            'retry_possible': payment_status[checkout_request_id].get('retry_possible', False)
        }
        
        # Always return success to M-Pesa
        return {
            "ResultCode": 0,
            "ResultDesc": "The service was accepted successfully",
            "ThirdPartyTransID": ""
        }
        
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {e}", exc_info=True)
        # Still return success to M-Pesa to prevent retries for invalid callbacks
        return {
            "ResultCode": 0,
            "ResultDesc": "The service was accepted successfully",
            "ThirdPartyTransID": ""
        }

@router.get("/payment-status/{checkout_request_id}")
async def get_payment_status(checkout_request_id: str):
    """
    Check the status of a payment
    """
    payment = payment_status.get(checkout_request_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

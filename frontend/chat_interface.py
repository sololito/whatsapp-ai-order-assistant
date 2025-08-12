import asyncio
import logging
import os
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackContext, CallbackQueryHandler, filters
)

# Add the project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.message_parser import MessageParser
from backend.inventory_checker import InventoryChecker
from backend.payment_handler import PaymentHandler
from backend.notifier import Notifier
from backend.order_logger import OrderLogger
from backend.delivery_option import DeliveryOption
from dotenv import load_dotenv
import os
import json
import datetime
from typing import Dict

load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SmartShopBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.parser = MessageParser()
        self.inventory = InventoryChecker()
        self.payment = PaymentHandler()
        self.notifier = Notifier()
        self.logger = OrderLogger()
        self.delivery = DeliveryOption()
        
        # User session data
        self.user_sessions = {}

    async def start(self, update: Update, context: CallbackContext) -> None:
        """Send welcome message when the command /start is issued."""
        user = update.effective_user
        welcome_message = (
            f"👋 Hello {user.first_name}! Welcome to SmartShop Bot.\n\n"
            "Where you can make an order at your own convenience and we deliver or pass by at your preferred time.\n\n"
            "*How to order:*\n"
            "• Just list the items with quantities you'd like to order. For example:\n"
            "  `2 loaves of bread and 1kg sugar`\n\n"
            "• To see what's available, ask:\n"
            "  `What items do you have?` or `Show me your products`\n\n"
            "We'll check availability and guide you through the process."
        )
        # Initialize or update user session
        user_id = user.id
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'state': 'START',
                'order': {},
                'conversation': []
            }
        else:
            self.user_sessions[user_id]['state'] = 'START'
            
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Handle incoming messages and process orders."""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Check for inventory listing requests
        if any(phrase in message_text.lower() for phrase in [
            'what do you have', 'what items do you have', 'what\'s available', 'show me your items',
            'what can i buy', 'list products', 'show inventory', 'what\'s in stock'
        ]):
            available_items = self.inventory.get_available_items()
            await update.message.reply_text(available_items)
            return
            
        message_text = message_text.lower()
        
        # Initialize user session if not exists
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'state': 'START',
                'order': {},
                'conversation': []
            }
        
        session = self.user_sessions[user_id]
        session['conversation'].append({'user': message_text})
        
        # Check for greetings
        if message_text in ['hi', 'hello', 'hey'] and session['state'] == 'START':
            welcome_message = (
                "👋 Hello! Welcome to SmartShop Bot.\n\n"
                "Where you can make an order at your own convenience and we deliver or pass by at your preferred time.\n\n"
                "*How to order:*\n"
                "Just list the items with quantities you'd like to order. For example:\n"
                "`2 loaves of bread and 1kg sugar`"
            )
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            return
            
        try:
            current_state = session['state']
            
            if current_state == 'START':
                await self._process_new_order(update, context, session, message_text)
            elif current_state == 'DELIVERY_OPTION':
                await self._process_delivery_option(update, context, session, message_text)
            elif current_state == 'DELIVERY_ADDRESS':
                await self._process_delivery_address(update, context, session, message_text)
            elif current_state == 'CONFIRMATION':
                await self._process_confirmation(update, context, session, message_text)
            elif current_state == 'AWAITING_MPESA_PHONE':
                await self._handle_mpesa_phone(update, context, session, message_text)
            elif current_state == 'AWAITING_MPESA_PIN':
                await self._process_mpesa_payment(update, context, session, message_text)
            else:
                await update.message.reply_text("I'm not sure what you mean. Type /start to begin a new order.")
                session['state'] = 'START'
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await update.message.reply_text("Sorry, an error occurred. Please try again or type /start to begin a new order.")
            session['state'] = 'START'

    async def _process_new_order(self, update: Update, context: CallbackContext, session: Dict, message: str) -> None:
        """Process initial order message"""
        try:
            # Parse the order message
            order_items = self.parser.parse_order_message(message)
            if not order_items:
                await update.message.reply_text(
                    "I couldn't understand your order. Please try again with a format like: \"2 loaves of bread and 1kg sugar\""
                )
                return
                
            import logging
            logger = logging.getLogger(__name__)
            
            # Debug log the order items
            logger.info(f"Order items: {order_items}")
            
            # Check inventory
            inventory_check = self.inventory.check_availability(order_items)
            logger.info(f"Inventory check result: {inventory_check}")
            
            available_items = inventory_check.get('available', [])
            unavailable_items = inventory_check.get('unavailable', [])
            
            # Debug log the structure of available_items
            logger.info(f"Available items structure: {available_items}")
            if available_items:
                logger.info(f"First available item: {available_items[0]}")
                logger.info(f"Type of first available item: {type(available_items[0])}")
            
            if not available_items:
                await update.message.reply_text("Sorry, none of the requested items are currently available.")
                return
                
            if unavailable_items:
                try:
                    # First, log the structure of the first unavailable item
                    logger.info(f"First unavailable item structure: {unavailable_items[0]}")
                    
                    # Try to format the unavailable items message
                    unavailable_text = []
                    for item in unavailable_items:
                        if isinstance(item, dict):
                            name = item.get('name', 'Unknown')
                            requested = item.get('requested', 'unknown')
                            available = item.get('available', 'unknown')
                            unavailable_text.append(f"- {name}: Requested {requested}, available {available}")
                        else:
                            logger.warning(f"Unexpected item type in unavailable_items: {type(item)}")
                            logger.warning(f"Item value: {item}")
                    
                    if unavailable_text:
                        await update.message.reply_text(
                            "Note: Some items are not available in the requested quantities:\n" + 
                            "\n".join(unavailable_text)
                        )
                except Exception as e:
                    logger.error(f"Error formatting unavailable items: {e}", exc_info=True)
                    logger.error(f"Unavailable items structure: {unavailable_items}")
            
            # Debug log before calculating total
            logger.info(f"Available items before total calculation: {available_items}")
            
            # Update session with order
            session['order']['items'] = available_items
            try:
                total = 0
                for item in available_items:
                    if isinstance(item, dict):
                        price = float(item.get('price', 0))
                        quantity = float(item.get('quantity', 0))
                        total += price * quantity
                    else:
                        logger.warning(f"Unexpected item type in available_items: {type(item)}")
                        logger.warning(f"Item value: {item}")
                
                session['order']['total'] = total
                logger.info(f"Total calculated: {session['order']['total']}")
            except Exception as e:
                logger.error(f"Error calculating order total: {e}", exc_info=True)
                if available_items:
                    logger.error(f"Problematic item: {available_items[0]}")
                raise
                
            session['state'] = 'DELIVERY_OPTION'
            
            # Show delivery options
            keyboard = [
                [InlineKeyboardButton("🚚 Delivery", callback_data='delivery')],
                [InlineKeyboardButton("🏪 Pickup", callback_data='pickup')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            order_summary = "\n".join([f"- {item['quantity']}x {item['name']} @ KES {item['price']:.2f}" 
                                     for item in available_items])
            
            await update.message.reply_text(
                f"📝 Order Summary:\n{order_summary}\n\n"
                f"Total: KES {session['order']['total']:.2f}\n\n"
                "Please choose delivery option:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error processing new order: {e}", exc_info=True)
            await update.message.reply_text("An error occurred while processing your order. Please try again.")

    async def _process_delivery_option(self, update: Update, context: CallbackContext, session: Dict, message: str) -> None:
        """Process delivery option selection"""
        # This is actually handled by the callback handler for inline buttons
        # If user typed instead of using buttons, we'll handle it here
        if update.message:
            if message.strip().lower() == 'delivery':
                session['state'] = 'DELIVERY_ADDRESS'
                await update.message.reply_text("Please enter your delivery address:")
            elif message.strip().lower() == 'pickup':
                await self._process_pickup_option(update, context, session)
            else:
                await update.message.reply_text("Please choose 'pickup' or 'delivery'")

    async def _process_delivery_address(self, update: Update, context: CallbackContext, session: Dict, message: str) -> None:
        """Process delivery address"""
        try:
            if not message.strip():
                await update.message.reply_text("Please provide a valid delivery address.")
                return
            
            # Calculate delivery fee based on address
            delivery_details = self.delivery.set_delivery_option('delivery', message.strip())
            
            # Update session with delivery details
            session['order']['delivery_option'] = {
                'option': 'delivery',
                'address': message.strip()
            }
            
            # Set the delivery fee in the order
            session['order']['delivery_fee'] = delivery_details.get('fee', 0)
            
            # Calculate and update the total
            subtotal = sum(item.get('total', 0) for item in session['order'].get('items', []))
            session['order']['subtotal'] = subtotal
            session['order']['total'] = subtotal + session['order']['delivery_fee']
            
            session['state'] = 'CONFIRMATION'
            await self._request_confirmation(update, context, session)
            
        except Exception as e:
            logger.error(f"Error processing delivery address: {e}", exc_info=True)
            await update.message.reply_text("Sorry, there was an error processing your delivery address. Please try again.")

    async def _process_pickup_option(self, update: Update, context: CallbackContext, session: Dict) -> None:
        """Process pickup option"""
        session['order']['delivery_option'] = {
            'option': 'pickup'
        }
        session['state'] = 'CONFIRMATION'
        await self._request_confirmation(update, context, session)

    async def _request_confirmation(self, update: Update, context: CallbackContext, session: Dict) -> None:
        """Request order confirmation from user and initiate payment"""
        try:
            total = sum(item['price'] * item['quantity'] for item in session['order'].get('items', []))
            delivery_fee = session['order'].get('delivery_fee', 0)
            total += delivery_fee
            
            # Format order summary
            summary = "\n".join([
                f"- {item['quantity']}x {item['name']} @ KES {item['price']:.2f}" 
                for item in session['order'].get('items', [])
            ])
            
            message = (
                f"🛒 *Order Summary* 🛒\n\n"
                f"{summary}\n\n"
                f"Delivery: {'KES ' + str(delivery_fee) + '.00' if delivery_fee > 0 else 'Free'}\n"
                f"*Total: KES {total:.2f}*\n\n"
                "Please confirm your order:"
            )
            
            # Create inline keyboard for confirmation
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data='confirm'),
                    InlineKeyboardButton("❌ Cancel", callback_data='cancel')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error processing pickup option: {e}", exc_info=True)
            await update.message.reply_text("Sorry, there was an error processing your pickup request. Please try again.")

    async def _initiate_payment(self, update: Update, context: CallbackContext, session: Dict) -> None:
        """Initiate M-Pesa payment process using test number from environment"""
        try:
            # Show processing message
            message = "💳 *Processing Payment*\n\n" \
                     "Please wait while we process your payment through M-Pesa..."
            
            if update.callback_query:
                msg = await update.callback_query.edit_message_text(
                    text=message,
                    parse_mode='Markdown'
                )
            else:
                msg = await update.message.reply_text(
                    text=message,
                    parse_mode='Markdown'
                )
            
            # Process payment with test number
            await self._process_mpesa_payment(update, context, session, "")
                
        except Exception as e:
            logger.error(f"Error initiating payment: {e}", exc_info=True)
            error_msg = "❌ Sorry, there was an error processing your payment. Please try again."
            if update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
    
    async def _handle_mpesa_phone(self, update: Update, context: CallbackContext, session: Dict, phone: str) -> None:
        """Handle M-Pesa phone number input (kept for backward compatibility)"""
        # Just process payment directly since we're using test number
        await self._process_mpesa_payment(update, context, session, "")
    
    async def _process_mpesa_payment(self, update: Update, context: CallbackContext, session: Dict, pin: str = "") -> None:
        """Process M-Pesa payment using test number from environment"""
        chat_id = None
        reply_func = None
        last_message = None
        
        try:
            # Get the message to update
            if update.callback_query:
                chat_id = update.callback_query.message.chat_id
                reply_func = update.callback_query.edit_message_text
                last_message = update.callback_query.message
            elif update.message:
                chat_id = update.message.chat_id
                reply_func = update.message.reply_text
            else:
                logger.error("No valid message or callback_query in update")
                return
            
            # Send new message instead of editing
            try:
                if reply_func == update.callback_query.edit_message_text:
                    await reply_func("⏳ Processing your payment...")
                else:
                    last_message = await reply_func("⏳ Processing your payment...")
            except Exception as e:
                logger.error(f"Error sending processing message: {e}")
                return
            
            # Get order details
            order_id = f"ORD-{int(time.time())}"
            amount = session['order'].get('total', 0)
            
            # Initiate STK push with test number (will be read from .env)
            payment_response = self.payment.initiate_stk_push(
                amount=amount,
                order_id=order_id,
                description="SmartShop Purchase"
            )
            
            # Log the raw payment response for debugging
            logger.info(f"Raw payment response: {payment_response}")
            
            # Check if payment was initiated successfully
            is_success = False
            response_message = ""
            
            # Check different possible success conditions
            if isinstance(payment_response, dict):
                # Case 1: Direct success with ResponseCode
                if payment_response.get('ResponseCode') == '0':
                    is_success = True
                    response_message = payment_response.get('ResponseDescription', 'Payment request sent successfully')
                # Case 2: Success status in root
                elif payment_response.get('status') == 'success':
                    is_success = True
                    response_message = payment_response.get('message', 'Payment request sent successfully')
                # Case 3: Success in data object
                elif isinstance(payment_response.get('data'), dict) and payment_response['data'].get('ResponseCode') == '0':
                    is_success = True
                    response_message = payment_response['data'].get('ResponseDescription', 'Payment request sent successfully')
            
            if is_success:
                # Check if this is a simulation
                is_simulation = payment_response.get('simulation', False)
                
                if is_simulation:
                    # Use the detailed simulation message from the payment handler
                    success_msg = payment_response.get('message', 
                        "✅ Payment simulation successful.\n\n"
                        f"Order ID: {order_id}\n"
                        f"Amount: KES {amount:,.2f}\n\n"
                        "ℹ️ This is a test transaction. No actual payment was processed."
                    )
                else:
                    # Real payment flow
                    success_msg = (
                        "✅ Payment request sent to your phone. Please check your M-Pesa menu "
                        "and enter your PIN to complete the transaction.\n\n"
                        f"Order ID: {order_id}\n"
                        f"Amount: KES {amount:,.2f}\n\n"
                        f"Status: {response_message}"
                    )
                
                try:
                    # Try to edit the last message if it exists and is editable
                    if (last_message and 
                        hasattr(last_message, 'edit_text') and 
                        callable(getattr(last_message, 'edit_text', None))):
                        try:
                            await last_message.edit_text(success_msg, parse_mode='Markdown')
                        except Exception as edit_error:
                            logger.warning(f"Could not edit message, sending new one: {edit_error}")
                            await context.bot.send_message(chat_id=chat_id, text=success_msg, parse_mode='Markdown')
                    else:
                        # Send a new message if we can't edit the last one
                        await context.bot.send_message(chat_id=chat_id, text=success_msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error sending success message: {e}")
                    # Try one more time with a simpler message
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"✅ Payment processed for order {order_id}",
                            parse_mode='Markdown'
                        )
                    except Exception as fallback_error:
                        logger.critical(f"Failed to send fallback message: {fallback_error}")
                
                # Update order status
                session['order']['payment_status'] = 'pending'
                session['order']['order_id'] = order_id
                
                # Log successful payment initiation
                logger.info(f"Payment initiated successfully. Order ID: {order_id}")
                
                # If this is a simulation, complete the order immediately
                if is_simulation:
                    # Update order status to completed for simulation
                    session['order']['payment_status'] = 'completed'
                    session['order']['order_id'] = order_id
                    await self._complete_order(update, context, session)
                return
                
            # If we get here, there was an error
            error_message = "Payment failed"
            error_code = "UNKNOWN"
            
            # Extract error information from different possible locations in the response
            if isinstance(payment_response, dict):
                if isinstance(payment_response.get('data'), dict):
                    error_message = payment_response['data'].get('errorMessage', 
                                                              payment_response.get('error_message', 'Payment failed'))
                    error_code = str(payment_response['data'].get('ResultCode', 
                                                               payment_response.get('error_code', 'UNKNOWN')))
                else:
                    error_message = payment_response.get('error_message', 'Payment failed')
                    error_code = str(payment_response.get('error_code', 'UNKNOWN'))
                
                # Special handling for timeout errors
                if error_code == 1037:  # User not reachable
                    logger.warning(f"M-Pesa STK Push timeout: {error_message}")
                    retry_message = (
                        "⚠️ *Payment Timeout*\n\n"
                        "We couldn't reach your phone with the payment request. This usually happens when:\n"
                        "• Your phone is off or has no network coverage\n"
                        "• You took too long to respond to the STK push\n\n"
                        "Please ensure your phone is on and has network signal, then try again."
                    )
                    
                    # Create retry keyboard
                    keyboard = [
                        [InlineKeyboardButton("🔄 Try Again", callback_data='retry_payment')],
                        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send the message with retry option
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=retry_message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    return
                    
                # For other errors
                logger.error(f"Payment failed with error: {error_message} (Code: {error_code})")
                error_text = (
                    f"❌ *Payment Failed*\n\n"
                    f"We encountered an error processing your payment.\n"
                    f"*Error:* {error_message}\n"
                    f"*Code:* {error_code}\n\n"
                    "Please try again or contact support if the issue persists."
                )
                
                # Send error message with retry option
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data='retry_payment')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                    
            else:
                # Handle payment failure
                error_msg = payment_response.get('error', 'Unknown error')
                if 'response' in payment_response and isinstance(payment_response['response'], dict):
                    error_msg = payment_response['response'].get('errorMessage', error_msg)
                
                error_text = (
                    f"❌ Payment failed: {error_msg}\n\n"
                    "Please try again or contact support if the issue persists."
                )
                logger.error(f"Payment failed. Details: {payment_response}")
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data='confirm')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                ])
                
                try:
                    if last_message and hasattr(last_message, 'edit_text'):
                        await last_message.edit_text(
                            error_text,
                            reply_markup=keyboard
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=error_text,
                            reply_markup=keyboard
                        )
                except Exception as e:
                    logger.error(f"Error sending error message: {e}")
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=error_text,
                            reply_markup=keyboard
                        )
                    except Exception as e2:
                        logger.error(f"Failed to send error message: {e2}")
                
                # Reset payment state
                session['state'] = 'CONFIRMATION'
                
        except Exception as e:
            logger.error(f"Error processing M-Pesa payment: {e}", exc_info=True)
            await update.message.reply_text("An error occurred while processing your payment. Please try again.")
            session['state'] = 'CONFIRMATION'

    async def _process_confirmation(self, update: Update, context: CallbackContext, session: Dict, message: str) -> None:
        """Process order confirmation and initiate payment"""
        try:
            # Calculate total if not already set
            if 'total' not in session['order']:
                subtotal = sum(item['price'] * item['quantity'] 
                             for item in session['order'].get('items', []))
                session['order']['total'] = subtotal + session['order'].get('delivery_fee', 0)
            
            # Show payment initiation message
            total = session['order']['total']
            payment_message = (
                f"💳 *Payment Required*\n\n"
                f"Total Amount: *KES {total:.2f}*\n\n"
                "We'll now redirect you to complete the payment via M-Pesa."
            )
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=payment_message,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    text=payment_message,
                    parse_mode='Markdown'
                )
            
            # Initiate payment flow
            await asyncio.sleep(1)  # Small delay for better UX
            await self._initiate_payment(update, context, session)
            
        except Exception as e:
            logger.error(f"Error in process confirmation: {e}", exc_info=True)
            error_msg = (
                "⚠️ *Payment Error*\n\n"
                "We encountered an issue while processing your payment. "
                "Please try again or contact support if the problem persists."
            )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data='confirm')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=error_msg,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    text=error_msg,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            session['state'] = 'CONFIRMATION'
        # Remove the else clause since we handle confirmation via buttons only now

    async def handle_phone_number(self, update: Update, context: CallbackContext) -> None:
        """Handle phone number input for payment"""
        try:
            phone = update.message.text.strip()
            
            if not self._validate_phone_number(phone):
                await update.message.reply_text(
                    "Invalid phone number format. Please enter a valid Kenyan phone number "
                    "starting with 254 (e.g., 254712345678)."
                )
                return
                
            # Format phone number if needed (e.g., add country code)
            if not phone.startswith('254'):
                phone = '254' + phone.lstrip('0')
                
            # Store phone number in session
            user_id = update.effective_user.id
            if user_id not in self.user_sessions:
                await update.message.reply_text("Session expired. Please start a new order with /start")
                return
                
            session = self.user_sessions[user_id]
            session['order']['phone'] = phone
            
            # Process payment
            await self._complete_order(update, context, session)
                
        except Exception as e:
            logger.error(f"Payment processing error: {e}", exc_info=True)
            await update.message.reply_text(
                "An error occurred while processing your payment. Please try again later."
            )

    async def _complete_order(self, update: Update, context: CallbackContext, session: Dict) -> None:
        """Complete order after successful payment"""
        try:
            order = session.get('order', {})
            
            # Generate receipt
            receipt_path = self.payment.generate_receipt(order)
            
            # Update inventory
            if 'items' in order:
                self.inventory.update_inventory(order['items'])
            
            # Prepare order data for logging
            # Handle delivery_option consistently - it might be a string or dict
            delivery_option = order.get('delivery_option', {})
            if isinstance(delivery_option, str):
                delivery_option_type = delivery_option
                delivery_address = ''
            else:
                delivery_option_type = delivery_option.get('option', 'pickup')
                delivery_address = delivery_option.get('address', '')
            
            order_data = {
                'order_id': order.get('order_id', f'order_{int(time.time())}'),
                'customer_phone': order.get('customer_phone', order.get('phone', '')),
                'items': order.get('items', []),
                'subtotal': sum(item.get('total', 0) for item in order.get('items', [])),
                'delivery_fee': order.get('delivery_fee', 0),
                'total': sum(item.get('total', 0) for item in order.get('items', [])) + order.get('delivery_fee', 0),
                'payment_status': 'pending',
                'delivery_option': {
                    'option': delivery_option_type,
                    'address': delivery_address
                },
                'receipt_id': receipt_path.split('/')[-1].split('.')[0] if receipt_path else ''
            }
            
            # Log order
            self.logger.log_order(order_data)
            
            # Notify shopkeeper
            self.notifier.notify_shopkeeper(order_data['order_id'], order_data['customer_phone'])
            
            # Generate and send receipt to customer
            receipt_content = self._generate_receipt_content(order_data, receipt_path or '')
            
            # Get the chat ID from the update
            chat_id = update.effective_chat.id
            
            # Send success message with receipt
            success_message = (
                "✅ *Payment Initiated Successfully!*\n\n"
                f"We've received your payment request for *KES {order_data['total']:,.2f}*. "
                "Please check your phone to complete the M-Pesa payment.\n\n"
                f"*Order ID:* {order_data['order_id']}\n"
                f"*Status:* Payment Pending\n\n"
                "You'll receive a confirmation once your payment is processed."
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=success_message,
                parse_mode='Markdown'
            )
            
            # Send receipt as a separate message
            await context.bot.send_message(
                chat_id=chat_id,
                text=receipt_content,
                parse_mode='Markdown'
            )
            
            # Thank you message with instructions for new orders
            thank_you_message = (
                "🌟 *Thank you for shopping with SmartShop AI!* 🌟\n\n"
                "Your order has been received and is being processed. "
                "If you'd like to make another purchase, simply list the items you need.\n\n"
                "For example:\n"
                "`2 loaves of bread and 1kg sugar`\n\n"
                "We're here to serve you better! 😊"
            )
            
            keyboard = [
                [InlineKeyboardButton("🛍️ New Order", callback_data='new_order')],
                [InlineKeyboardButton("❌ Exit", callback_data='exit')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=thank_you_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Clear session but keep the state as COMPLETED
            session['state'] = 'COMPLETED'
            session['order'] = {}
            
        except Exception as e:
            logger.error(f"Error completing order: {e}", exc_info=True)
            error_message = (
                "⚠️ *Order Processing Error*\n\n"
                "We've received your payment, but encountered an issue processing your order. "
                "Please contact support with your order details."
            )
            
            chat_id = update.effective_chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message,
                parse_mode='Markdown'
            )

    def _generate_order_summary(self, order: Dict) -> str:
        """Generate order summary message with improved formatting"""
        items_text = "\n".join(
            f"• {item['quantity']} x {item['name']} @ KES {item['price']:,.2f} = KES {item['total']:,.2f}"
            for item in order['items']
        )
        
        subtotal = sum(item['total'] for item in order['items'])
        total = subtotal + (order.get('delivery_fee', 0))
        
        summary = (
            "*🛒 SmartShop Order Summary*\n\n"
            f"{items_text}\n\n"
            f"*Subtotal:* KES {subtotal:,.2f}\n"
            f"*Delivery Fee:* KES {order.get('delivery_fee', 0):,.2f}\n"
            f"*Total:* KES {total:,.2f}\n\n"
            f"*Delivery Option:* {order['delivery_option']['option'].capitalize()}\n"
        )
        
        if 'delivery_address' in order:
            summary += f"*Delivery Address:* {order['delivery_address']}\n"
        
        return summary

    def _generate_receipt_content(self, order: Dict, receipt_path: str) -> str:
        """Generate receipt message for customer"""
        # Safely get delivery option details
        delivery_option = order.get('delivery_option', {})
        if isinstance(delivery_option, str):
            delivery_option = {'option': delivery_option, 'address': ''}
            
        receipt_content = (
            f"*SmartShop Receipt*\n\n"
            f"Order ID: {order.get('order_id', 'N/A')}\n"
        )
        
        # Add delivery address if it's a delivery order
        if delivery_option.get('option') == 'delivery' and delivery_option.get('address'):
            receipt_content += f"\n*Delivery Address:*\n{delivery_option['address']}\n"
        
        # Add items
        receipt_content += "\n*Order Details:*\n"
        for item in order.get('items', []):
            receipt_content += (
                f"• {item.get('quantity', 1):.1f} x {item.get('name', 'Item')} "
                f"@ KES {item.get('price', 0):.2f} = KES {item.get('total', 0):.2f}\n"
            )
        
        receipt_content += (
            f"\n*Order Summary:*\n"
            f"Subtotal: KES {order.get('subtotal', 0):.2f}\n"
            f"Delivery Fee: KES {order.get('delivery_fee', 0):.2f}\n"
            f"*Total: KES {order.get('total', 0):.2f}*\n\n"
            f"*Payment Information:*\n"
            f"Payment Method: {order.get('payment_method', 'M-Pesa')}\n"
            f"Status: {order.get('status', 'Paid')}\n\n"
            f"Thank you for shopping with us! "
            f"Your order will be delivered to the provided address.\n"
            f"For any inquiries, please contact our support."
        )
        
        return receipt_content

    def _validate_phone_number(self, phone: str) -> bool:
        """Validate Kenyan phone number format"""
        import re
        pattern = r'^254[17]\d{8}$'
        return re.match(pattern, phone) is not None

    async def button_handler(self, update: Update, context: CallbackContext) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if user_id not in self.user_sessions:
            await query.edit_message_text("Your session has expired. Please type /start to begin a new order.")
            return
            
        session = self.user_sessions[user_id]
        
        try:
            if query.data == 'delivery':
                session['order']['delivery_option'] = {
                    'option': 'delivery',
                    'address': ''
                }
                session['state'] = 'DELIVERY_ADDRESS'
                await query.edit_message_text("Please enter your delivery address:")
                
            elif query.data == 'pickup':
                session['order']['delivery_option'] = {
                    'option': 'pickup'
                }
                await self._process_pickup_option(update, context, session)
                
            elif query.data == 'confirm':
                # Process order confirmation and initiate payment
                try:
                    session['state'] = 'CONFIRMATION'
                    await self._process_confirmation(update, context, session, "")
                except Exception as e:
                    logger.error(f"Error in confirm handler: {e}", exc_info=True)
                    await query.edit_message_text(
                        "❌ An error occurred while processing your confirmation. Please try again.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Try Again", callback_data='confirm')],
                            [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                        ])
                    )
                
            elif query.data == 'cancel':
                await query.edit_message_text("Order cancelled. Type /start to begin a new order.")
                session['state'] = 'START'
                
            elif query.data == 'cancel_payment':
                # Handle payment cancellation
                await query.edit_message_text("Payment cancelled. Type /start to begin a new order.")
                session['state'] = 'START'
                
            elif query.data == 'new_order':
                # Start a new order
                session['state'] = 'START'
                session['order'] = {}
                await query.edit_message_text(
                    "🛒 *New Order*\n\n"
                    "Please enter the items you'd like to order, one per line in the format:\n"
                    "`2x Pizza Margherita` or `1x Coffee`\n\n"
                    "Type /cancel at any time to cancel the order.",
                    parse_mode='Markdown'
                )
                
            elif query.data == 'exit':
                # End the session
                await query.edit_message_text(
                    "Thank you for shopping with us! If you need anything else, just type /start to begin a new order. Have a great day! 😊"
                )
                session['state'] = 'START'
                session['order'] = {}
                
            elif query.data.startswith('retry_payment_'):
                # Handle payment retry
                session['state'] = 'AWAITING_MPESA_PHONE'
                await query.edit_message_text("Please enter your M-Pesa registered phone number (format: 2547XXXXXXXX):")
                
        except Exception as e:
            logger.error(f"Error in button handler: {e}", exc_info=True)
            
            # Add retry option for payment errors
            if session['state'] in ['AWAITING_MPESA_PHONE', 'AWAITING_MPESA_PIN']:
                keyboard = [
                    [InlineKeyboardButton("🔄 Retry Payment", callback_data='retry_payment')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "Sorry, an error occurred. Please try again.",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("Sorry, an error occurred. Please type /start to begin a new order.")
                session['state'] = 'START'

    async def error_handler(self, update: Update, context: CallbackContext) -> None:
        """Log errors"""
        # Log the error
        logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
        
        # Try to notify the user about the error
        try:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Sorry, an error occurred while processing your request. Please try again or contact support if the issue persists."
                )
        except Exception as e:
            logger.error(f"Error sending error message to user: {e}")

    async def run(self):
        """Start the bot in polling mode.
        
        This method is now async to work with the new server setup.
        """
        # Create the Application and pass it your bot's token
        application = Application.builder().token(self.token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.button_handler))
        application.add_error_handler(self.error_handler)
        
        # Start the bot with polling
        logger.info("Starting bot in polling mode...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Keep the application running until manually stopped
        try:
            while True:
                await asyncio.sleep(1)
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Shutting down bot...")
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

if __name__ == '__main__':
    bot = SmartShopBot()
    bot.run()
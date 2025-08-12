import requests
from dotenv import load_dotenv
import os
import serial
import time
import json
from typing import Dict

load_dotenv()

class Notifier:
    def __init__(self):
        self.sms_api_key = os.getenv('SMS_API_KEY')
        self.sms_sender_id = os.getenv('SMS_SENDER_ID')
        self.serial_port = os.getenv('BELL_SERIAL_PORT', '/dev/ttyUSB0')
        
    def send_sms_notification(self, phone: str, message: str) -> bool:
        """Send SMS notification to shopkeeper"""
        if not self.sms_api_key:
            return False
            
        url = "https://api.smsapi.com/sms.do"
        params = {
            'to': phone,
            'from': self.sms_sender_id,
            'message': message,
            'format': 'json',
            'encoding': 'utf-8',
            'api_key': self.sms_api_key
        }
        
        response = requests.get(url, params=params)
        return response.status_code == 200

    def trigger_bell(self, duration: float = 0.5):
        """Trigger physical bell connected via serial port"""
        try:
            with serial.Serial(self.serial_port, 9600, timeout=1) as ser:
                ser.write(b'1')  # Signal to trigger bell
                time.sleep(duration)
                ser.write(b'0')  # Signal to stop bell
        except serial.SerialException:
            print("Failed to trigger bell - serial connection error")

    def notify_shopkeeper(self, order_id: str, customer_phone: str):
        """Notify shopkeeper via both bell and SMS"""
        shop_info = self._load_shop_info()
        if not shop_info:
            return False
        
        # Trigger physical bell
        self.trigger_bell()
        
        # Send SMS if shopkeeper phone is available
        if 'shopkeeper_phone' in shop_info:
            message = f"New order #{order_id} from {customer_phone}"
            return self.send_sms_notification(shop_info['shopkeeper_phone'], message)
        return False

    def _load_shop_info(self) -> Dict:
        """Load shop information from JSON file"""
        try:
            with open('data/shop_info.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
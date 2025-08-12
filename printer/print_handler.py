import os
import json
from escpos.printer import Usb
from dotenv import load_dotenv

load_dotenv()

class PrintHandler:
    def __init__(self):
        # Load printer configuration
        self.vendor_id = int(os.getenv('PRINTER_VENDOR_ID', 0x0416))
        self.product_id = int(os.getenv('PRINTER_PRODUCT_ID', 0x5011))
        self.printer = self._initialize_printer()

    def _initialize_printer(self):
        """Initialize USB printer connection"""
        try:
            return Usb(self.vendor_id, self.product_id)
        except Exception as e:
            print(f"Failed to initialize printer: {e}")
            return None

    def print_receipt(self, receipt_path: str):
        """Print receipt from JSON file"""
        if not self.printer:
            print("Printer not available")
            return False

        try:
            with open(receipt_path, 'r') as f:
                receipt = json.load(f)
            
            # Print header
            self.printer.set(align='center')
            self.printer.text("\n")
            self.printer.text(receipt['shop_info'].get('shop_name', 'SmartShop') + "\n")
            self.printer.text(receipt['shop_info'].get('address', '') + "\n")
            self.printer.text("Tel: " + receipt['shop_info'].get('phone', '') + "\n")
            self.printer.text("\n")
            self.printer.text("--------------------------------\n")
            
            # Print receipt info
            self.printer.set(align='left')
            self.printer.text(f"Receipt #: {receipt['receipt_id']}\n")
            self.printer.text(f"Date: {receipt['date']}\n")
            self.printer.text(f"Customer: {receipt['customer']}\n")
            self.printer.text("\n")
            
            # Print items
            self.printer.text("ITEMS:\n")
            for item in receipt['items']:
                self.printer.text(f"{item['quantity']} x {item['name']}\n")
                self.printer.text(f"  @ {item['price']:.2f} = {item['total']:.2f}\n")
            
            self.printer.text("\n")
            self.printer.text("--------------------------------\n")
            
            # Print totals
            self.printer.text(f"Subtotal: {receipt['subtotal']:.2f}\n")
            if receipt.get('delivery_fee', 0) > 0:
                self.printer.text(f"Delivery: {receipt['delivery_fee']:.2f}\n")
            self.printer.text(f"TOTAL: {receipt['total']:.2f}\n")
            self.printer.text("\n")
            
            # Print payment info
            self.printer.text(f"Payment: {receipt['payment_method']}\n")
            self.printer.text(f"Status: {receipt['payment_status']}\n")
            
            if receipt.get('delivery_option') == 'delivery':
                self.printer.text("\n")
                self.printer.text("DELIVERY ADDRESS:\n")
                self.printer.text(f"{receipt.get('delivery_address', '')}\n")
            
            # Print footer
            self.printer.text("\n")
            self.printer.set(align='center')
            self.printer.text("Thank you for shopping with us!\n")
            self.printer.text("\n\n\n")
            
            # Cut paper
            self.printer.cut()
            
            return True
        except Exception as e:
            print(f"Error printing receipt: {e}")
            return False
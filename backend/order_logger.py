import csv
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from typing import Dict

load_dotenv()

class OrderLogger:
    def __init__(self):
        self.log_file = 'data/order_logs.csv'
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        """Create log file with headers if it doesn't exist"""
        try:
            with open(self.log_file, 'x', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'order_id', 'timestamp', 'customer_phone', 'items', 
                    'subtotal', 'delivery_fee', 'total', 'payment_status',
                    'delivery_option', 'receipt_id'
                ])
        except FileExistsError:
            pass

    def log_order(self, order_details: Dict):
        """Log completed order to CSV file"""
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                order_details.get('order_id'),
                datetime.now().isoformat(),
                order_details.get('customer_phone'),
                json.dumps(order_details.get('items', [])),
                order_details.get('subtotal', 0),
                order_details.get('delivery_fee', 0),
                order_details.get('total', 0),
                order_details.get('payment_status', 'pending'),
                order_details.get('delivery_option', 'pickup'),
                order_details.get('receipt_id', '')
            ])

    def generate_monthly_report(self, month: int, year: int) -> Dict:
        """Generate monthly sales report"""
        monthly_orders = []
        total_sales = 0
        total_orders = 0
        
        with open(self.log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                order_date = datetime.fromisoformat(row['timestamp'])
                if order_date.month == month and order_date.year == year:
                    monthly_orders.append(row)
                    total_sales += float(row['total'])
                    total_orders += 1
        
        return {
            'month': month,
            'year': year,
            'total_orders': total_orders,
            'total_sales': total_sales,
            'average_order_value': total_sales / total_orders if total_orders > 0 else 0,
            'orders': monthly_orders
        }

    def send_monthly_report_email(self, month: int, year: int, recipient: str):
        """Send monthly report via email"""
        report = self.generate_monthly_report(month, year)
        
        # Email content
        subject = f"SmartShop Monthly Report - {month}/{year}"
        body = f"""
        SmartShop Monthly Sales Report
        ----------------------------
        Month: {month}/{year}
        Total Orders: {report['total_orders']}
        Total Sales: KES {report['total_sales']:,.2f}
        Average Order Value: KES {report['average_order_value']:,.2f}
        
        Top Items:
        {self._get_top_items(report)}
        """
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = os.getenv('SMTP_EMAIL')
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT')) as server:
            server.starttls()
            server.login(os.getenv('SMTP_EMAIL'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)

    def _get_top_items(self, report: Dict) -> str:
        """Get top selling items from report"""
        item_counts = {}
        for order in report['orders']:
            items = json.loads(order['items'])
            for item in items:
                item_name = item['name']
                item_counts[item_name] = item_counts.get(item_name, 0) + item['quantity']
        
        sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return "\n".join([f"{item[0]}: {item[1]}" for item in sorted_items])
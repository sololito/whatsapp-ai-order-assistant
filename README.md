# WhatsApp AI Order Assistant with M-Pesa Integration

An AI-powered WhatsApp assistant that helps local businesses automate order management through WhatsApp. The system enables customers to browse products, place orders, and make payments via M-Pesa, all within the familiar WhatsApp interface.

## Features

- AI-powered WhatsApp chat interface
- Product catalog and inventory management
- Order processing and confirmation
- M-Pesa payment integration
- Delivery option management
- Order logging and tracking
- Responsive and user-friendly interface

## Project Structure

```
chatbot/
├── backend/                    # Backend services and business logic
│   ├── delivery_option.py      # Delivery option management
│   ├── inventory_checker.py    # Inventory management and validation
│   ├── mpesa_callback.py       # M-Pesa payment callbacks
│   ├── notifier.py            # Notification services
│   ├── order_logger.py        # Order logging and tracking
│   └── payment_handler.py     # M-Pesa payment processing
│
├── data/                      # Data storage
│   ├── inventory.json         # Product catalog and stock levels
│   ├── order_logs.csv         # Order history
│   └── shop_info.json         # Shop information and settings
│
├── frontend/                  # Frontend components
│   ├── chat_interface.py      # WhatsApp chat interface
│   └── message_parser.py      # Message parsing and processing
│
├── receipts/                  # Generated order receipts
├── printer/                   # Receipt printing functionality
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
└── run.py                    # Application entry point
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- WhatsApp Business API access (via Twilio or direct)
- M-Pesa Daraja API credentials

### 2. Installation

1. Clone the repository
   ```bash
   git clone <repository-url>
   cd chatbot
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configuration

1. Create a `.env` file with your configuration:
   ```
   # WhatsApp Configuration
   WHATSAPP_ACCOUNT_SID=your_whatsapp_sid
   WHATSAPP_AUTH_TOKEN=your_whatsapp_token
   WHATSAPP_NUMBER=whatsapp:+1234567890

   # M-Pesa Configuration
   MPESA_CONSUMER_KEY=your_consumer_key
   MPESA_CONSUMER_SECRET=your_consumer_secret
   MPESA_SHORTCODE=your_shortcode
   MPESA_PASSKEY=your_passkey
   MPESA_CALLBACK_URL=https://your-domain.com/mpesa-callback
   ```

2. Update the inventory and shop information in the `data/` directory

### 4. Running the Application

Start the application:
Coming soon...

---

## 🏁 Run the Project

```bash
python bot.py
```

If testing locally with M-Pesa:
```bash
ngrok http 5000
```

---

## 🏆 Hackathon Submission

Built for the [Simplify AI Tools Hackathon 2025](https://unstop.com/hackathons/simplify-ai-tools-hackathon-2025-926372). Designed to empower **local business owners**, especially in **Africa**, with a tool that simplifies ordering, communication, and payment.

---

## 📜 License

MIT License

---

## 🙌 Contributors

- Solomon Odipo (Lead Developer & Architect)


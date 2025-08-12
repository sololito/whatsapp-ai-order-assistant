
# 🛒 WhatsApp AI Order Assistant with M-Pesa Payments

An AI-powered WhatsApp assistant for local businesses that lets customers place orders, request delivery or pickup, confirm purchases, and pay instantly via M-Pesa. Designed for the Simplify AI Tools Hackathon 2025, it enables shop owners and micro-vendors to automate order processing, fulfilment, and payments — all without a complicated app.

---

## 🚀 Features

- 🧠 AI-powered understanding of WhatsApp messages
- ✅ Order confirmation and response automation
- 📦 Inventory and order logging 
- 💰 M-Pesa STK Push payment integration (Daraja API)
- 🔔 WhatsApp bot notifications
- 🌍 Easy to deploy and use

---

## 📁 Project Structure

```
whatsapp-ai-order-assistant/
├── README.md                   # Project documentation
├── requirements.txt            # Dependencies
├── .env                        # Secrets (Twilio, Google, Safaricom keys)
├── bot.py                      # Main WhatsApp bot logic
├── mpesa.py                    # M-Pesa STK push logic
├── google_sheets.py            # Google Sheets API integration
├── webhook_handler.py          # Webhook for receiving payment confirmations
├── templates/
│   └── response_templates.json # AI prompt templates
├── static/
│   └── logs/                   # Logs of orders and payments
├── utils/
│   └── helpers.py              # Helper functions
└── ngrok_setup/                # For local development tunneling
```

---

## ⚙️ Setup Instructions

### 1. 🔐 Environment Variables

Create a `.env` file with the following:

```
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_SHEET_CREDENTIALS_JSON=path/to/credentials.json

MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_SHORTCODE=your_paybill_or_till_number
MPESA_PASSKEY=your_passkey
MPESA_CALLBACK_URL=https://yourdomain.com/mpesa-callback
```

---

### 2. 📦 Install Requirements

```bash
pip install -r requirements.txt
```

---

### 3. 📱 WhatsApp Integration

- Sign up at [Twilio](https://www.twilio.com/whatsapp) and set your webhook to your server or `ngrok` tunnel.

---

### 4. 📊 Google Sheets Setup

- Create a Google Sheet
- Share with your service account email (`*.gserviceaccount.com`)
- Place credentials in `google_sheets.py`

---

### 5. 💸 M-Pesa STK Push Setup

- Register at [Safaricom Developer Portal](https://developer.safaricom.co.ke)
- Use Daraja API v2
- Set callback URL to `/mpesa-callback`
- Handle confirmation in `webhook_handler.py`

---

### 6. 🔄 Full Bot Flow

1. Customer sends a message: “I want 2 loaves and 1 milk”
2. Bot replies with: “Confirm order: 2 loaves, 1 milk. Total: KES 375. Reply ‘Yes’ to continue.”
3. If user says "Yes":
    - Bot initiates M-Pesa STK push
    - Logs payment and order in Google Sheet

---

## 📷 Screenshots

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


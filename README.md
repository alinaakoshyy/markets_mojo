# 💸 Markets Mojo — FastAPI + MongoDB Account Manager

Markets Mojo is a backend service built with **FastAPI** and **MongoDB** to manage users, accounts, withdrawals, and balances efficiently. It supports multiple accounts per user, merchant-type classification, and detailed transaction histories.

---

## 🚀 Features

- ✅ Create users and multiple accounts
- 💰 Withdraw or increment cash per account
- 📊 Maintain summaries for each user's accounts
- 🔐 Distinct collections for:
  - `users`: personal info
  - `accounts`: one document per account
  - `withdrawals`: tracks all withdrawals
  - `user_accounts_summary`: overview per user

---

## 📁 Project Structure

markets-mojo/
├── main.py # FastAPI app
├── .env # Environment variables (URI, etc.)
├── .gitignore
└── README.md

---

## ⚙️ API Endpoints

### 🔹 Create User + Account

```http
POST /create
{
  "user_name": "your_name",
  "age": 21,
  "email": "alina@example.com",
  "contact_number": "9876543210",
  "merchant_type": "business",
  "initial_amount": 50000
}


POST /withdrawal
{
  "account_id": 100001,
  "withdrawal_amount": 5000
}


POST /cash_inc
{
  "account_id": 100001,
  "increment_amount": 2000
}


GET /info/user/{user_id}
GET /info/account/{account_id}


🧠 Tech Stack
FastAPI – blazing fast Python backend

MongoDB – flexible NoSQL database

MongoDB Compass – local DB management

Uvicorn – ASGI server



🔧 Setup Instructions
Clone the repo

bash
git clone https://github.com/your-username/markets-mojo.git
cd markets-mojo
Create .env file

ini
LOCAL_URI=mongodb://localhost:27017
USE_ATLAS=false
Install dependencies

bash
pip install -r requirements.txt
Run the app

bash
uvicorn main:app --reload



👩‍💻 Built by
Alina Koshy 💚


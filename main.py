# IMPORTS
from fastapi import FastAPI
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from fastapi import HTTPException, status
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import os
from dotenv import load_dotenv
from enum import Enum

# APP
app = FastAPI()


# MODELS
class Merchant_type(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    ORGANIZATION = "organization"
    OTHERS = "others"


class Money(BaseModel):
    user_name: str
    age: int
    email: str
    contact_number: str
    merchant_type: Merchant_type
    initial_amount: int


class Fullnote(BaseModel):
    user_name: str
    age: int
    email: str
    contact_number: str
    user_id: int
    account_id: int
    merchant_type: Merchant_type
    date_of_creation: datetime
    initial_amount: int
    current_amount: int
    withdrawals: List[dict] = []


class WithdrawalRequest(BaseModel):
    account_id: int
    withdrawal_amount: int


class CashIncrementRequest(BaseModel):
    account_id: int
    increment_amount: int


# In-memory storage (for demonstration purposes)
update: List[Fullnote] = []  # This will be replaced by MongoDB storage

# Load environment variables
load_dotenv()
use_atlas = os.getenv("USE_ATLAS", "false").lower() == "true"
MongoURI = os.getenv("ATLAS_URI") if use_atlas else os.getenv("LOCAL_URI")


# MongoDB setup
client = MongoClient(MongoURI)
db = client["markets_mojo"]
accounts_collection = db["accounts"]
users_collection = db["users"]
withdrawals_collection = db["withdrawals"]
user_accounts_summary_collection = db["user_accounts_summary"]


# ROUTES

# HOME ROUTE
@app.get("/")
def home():
    return {"message": "Welcome to the Markets MOJO 💚"}


# CREATE USER ROUTE
@app.post("/create", status_code=status.HTTP_201_CREATED)
def create_user(money: Money):
    user_count = users_collection.count_documents({})

    money_data = money.dict()

    # check if user already exists
    existing_user = users_collection.find_one(
        {"user_name": {
            "$regex": f"^{money_data['user_name']}$", "$options": "i"}}
    )

    # user_id = existing_user["user_id"] if existing_user else 1
    if existing_user:
        user_id = existing_user["user_id"]
    else:
        # Get the last user_id and increment it
        last_user = users_collection.find_one(sort=[("user_id", -1)])
        if last_user is None:
                user_id = 1001
        else:
                user_id = last_user["user_id"] + 1

        # insert in users collection
        users_collection.insert_one({
            "user_id": user_id,
            "user_name": money_data["user_name"],
            "age": money_data["age"],
            "email": money_data["email"],
            "contact_number": money_data["contact_number"],
            "merchant_type": money_data["merchant_type"],
        })

    # Generate a unique account_id
    last_account = accounts_collection.find_one(
        sort=[("account_id", -1)])
    account_id = last_account["account_id"] + 1 if last_account else 100001

    # insert in accounts collection
    accounts_collection.insert_one({
        "account_id": account_id,
        "user_id": user_id,
        "initial_amount": money_data["initial_amount"],
        "current_amount": money_data["initial_amount"],
        "date_of_creation": datetime.utcnow(),
        "merchant_type": money_data["merchant_type"],
    })

    # insert withdrawals collection
    withdrawals_collection.insert_one({
        "account_id": account_id,
        "withdrawals": [],
    })

    # update user_accounts_summary_collection
    summary = user_accounts_summary_collection.find_one({"user_id": user_id})
    new_account = {
        "account_id": account_id,
        "current_amount": money_data["initial_amount"],
        "merchant_type": money_data["merchant_type"],
    }

    if summary:
        user_accounts_summary_collection.update_one(
            {"user_id": user_id},
            {"$push": {"accounts": new_account}}
        )
    else:
        user_accounts_summary_collection.insert_one({
            "user_id": user_id,
            "accounts": [new_account]
        })

    return {
        "message": "User and account created successfully",
        "user_name": money_data["user_name"],
        "account_id": account_id,
        "user_id": user_id,
    }

# GET USER INFO ROUTE

# by user_id
@app.get("/info/user/{user_id}")
def get_user_accounts_summary(user_id: int):
    accounts = list(accounts_collection.find({"user_id": user_id}, {"_id": 0}))

    if not accounts:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user_id,
        "accounts_summary": accounts
    }


# by account_id
@app.get("/info/account/{account_id}")
def get_user_details(account_id: int):
    account = accounts_collection.find_one({"account_id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    withdrawals = withdrawals_collection.find_one(
        {"account_id": account_id}, {"_id": 0})
    
    account["_id"] = str(account["_id"])  # Convert ObjectId to string for JSON serialization

    return {
        "account_info": account,
        "withdrawals": withdrawals
    }



# WITHDRAWAL ROUTE
@app.post("/withdrawal")
def withdraw_money(request: WithdrawalRequest):

    # check if user exists
    account = accounts_collection.find_one({"account_id": request.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_collection.find_one({"user_id": account["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found in users collection")

    if request.withdrawal_amount > account["current_amount"]:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    


    # update the user's current amount
    new_balance = account["current_amount"] - request.withdrawal_amount
    accounts_collection.update_one(
        {"account_id": request.account_id},
        {"$set": {"current_amount": new_balance}}
    )

    withdrawals_collection.update_one(
        {"account_id": request.account_id},
        {"$push": {"withdrawals": {
            "amount": request.withdrawal_amount,
            "date": datetime.utcnow()
        }}},
        upsert=True
    )

    # update the summary collection
    user_accounts_summary_collection.update_one(
        {"user_id": account["user_id"], "accounts.account_id": request.account_id},
        {"$set": {
            "accounts.$.current_amount": new_balance
        }}
    )

    # fetch all withdrawals for the account
    withdrawals_doc = withdrawals_collection.find_one(
        {"account_id": request.account_id}, {"_id": 0})

    return {
        "message": "Withdrawal successful",
        "user_name": user["user_name"],
        "user_id": user["user_id"],
        "account_id": request.account_id,
        "merchant_type": account["merchant_type"],
        "initial_amount": account["initial_amount"],
        "withdrawal_amount": request.withdrawal_amount,
        "new_balance": new_balance,
        "withdrawals": withdrawals_doc.get("withdrawals", [])  
      }


# CASH INCREMENT ROUTE
@app.post("/cash_inc")
def cash_increment(request: CashIncrementRequest):
    # find the account
    account = accounts_collection.find_one({"account_id": request.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # update the current amount
    new_amount = account["current_amount"] + request.increment_amount

    # update the accounts collection in the database
    accounts_collection.update_one(
        {"account_id": request.account_id},
        {"$set": {"current_amount": new_amount}}
    )

    # update the users collection
    users_collection.update_one(
        {"account_id": request.account_id},
        {"$set": {"current_amount": new_amount}}
    )

    # update the user_accounts_summary_collection
    user_id = account["user_id"]
    summary_doc = user_accounts_summary_collection.find_one(
        {"user_id": user_id})
    if summary_doc:
        updated_accounts = []
        for acc in summary_doc["accounts"]:
            if acc["account_id"] == request.account_id:
                acc["current_amount"] = new_amount
            updated_accounts.append(acc)

        user_accounts_summary_collection.update_one(
            {"user_id": user_id},
            {"$set": {"accounts": updated_accounts}}
        )


        user = users_collection.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found in users collection")
        


        summary = user_accounts_summary_collection.find_one({"user_id": user_id})
        accounts_info = summary.get("accounts", []) if summary else []
        


    return {
        "message": "Cash increment successful",
        "user_id": user_id,
        "user_name": user["user_name"],
        "account_id": request.account_id,
        "merchant_type": account["merchant_type"],
        "increment_amount": request.increment_amount,
        "new_balance": new_amount,
        "all_accounts": accounts_info
    }


# TEST INSERT ROUTE
@app.post("/test_insert")
def test_insert():
    dummy = {
        "name": "test_user",
        "age": 25
    }
    result = users_collection.insert_one(dummy)
    return {"inserted_id": str(result.inserted_id)}

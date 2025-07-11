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

# APP
app = FastAPI()


# MODELS
class Money(BaseModel):
    user_name: str
    age: int
    email: str
    contact_number: str
    initial_amount: int


class Fullnote(BaseModel):
    user_name: str
    age: int
    email: str
    contact_number: str
    user_id: int
    account_id: int
    date_of_creation: datetime
    initial_amount: int
    current_amount: int
    withdrawals: List[dict] = []


class WithdrawalRequest(BaseModel):
    account_id: int
    withdrawal_amount: int


# In-memory storage (for demonstration purposes)
update: List[Fullnote] = []  # This will be replaced by MongoDB storage

# Load environment variables
load_dotenv()
use_atlas = os.getenv("USE_ATLAS", "false").lower() == "true"
MongoURI = os.getenv("ATLAS_URI") if use_atlas else os.getenv("LOCAL_URI")


# MongoDB setup
client = MongoClient(MongoURI)
db = client["markets_mojo"]
users_collection = db["users"]


# ROUTES

# HOME ROUTE
@app.get("/")
def home():
    return {"message": "Welcome to the Markets MOJO 💚"}


# CREATE USER ROUTE
@app.post("/create", response_model=Fullnote, status_code=status.HTTP_201_CREATED)
def create_user(money: Money):
    user_count = users_collection.count_documents({})
    money_data = money.dict()

    # Add computed fields
    money_data["date_of_creation"] = datetime.utcnow()
    money_data["current_amount"] = money_data["initial_amount"]
    money_data["user_id"] = user_count + 1
    money_data["account_id"] = user_count + 1

    # Insert into MongoDB
    result = users_collection.insert_one(money_data)

    print("✅ Inserted:", money_data)
    print("✅ ID:", result.inserted_id)

    return Fullnote(**money_data)


# GET USER INFO ROUTE
@app.get("/info/{account_id}", response_model=Fullnote)
def get_user_info(account_id: int):
    user = users_collection.find_one({"account_id": account_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return Fullnote(
        user_name=user["user_name"],
        age=user["age"],
        email=user["email"],
        contact_number=user["contact_number"],
        user_id=user["user_id"],
        account_id=user["account_id"],
        date_of_creation=user["date_of_creation"],
        initial_amount=user["initial_amount"],
        current_amount=user["current_amount"],
        withdrawals=user.get("withdrawals", [])
    )


# WITHDRAWAL ROUTE
@app.post("/withdrawal")
def withdraw_money(request: WithdrawalRequest):
    user = users_collection.find_one({"account_id": request.account_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

     # Initialize withdrawals if not already present
    if "withdrawals" not in user:
        user["withdrawals"] = []

    if request.withdrawal_amount > user["current_amount"]:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    new_enrty = {
        "withdrawal_amount": request.withdrawal_amount,
        "date": datetime.utcnow()
    }

    updated_withdrawal = user["withdrawals"] + [new_enrty]
    updated_current_amount = user["current_amount"] - request.withdrawal_amount

    users_collection.update_one(
        {"account_id": request.account_id},
        {
            "$set": {
                "withdrawals": updated_withdrawal,
                "current_amount": updated_current_amount
            }
        }
    )

    return {
        "message": "Withdrawal successful",
        "updated_withdrawal": updated_withdrawal,
        "updated_current_amount": updated_current_amount
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

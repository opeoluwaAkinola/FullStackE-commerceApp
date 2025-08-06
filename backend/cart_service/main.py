# Shopping Cart Microservice
# File: cart_service/main.py

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pymongo import AsyncMongoClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import datetime
from bson import ObjectId
import os
import httpx
import asyncio

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncMongoClient(MONGODB_URL)
database = client.ecommerce
carts_collection = database.carts
cart_items_collection = database.cart_items

# Service URLs
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000")

app = FastAPI(title="Shopping Cart Service", version="1.0.0")


# Pydantic models
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def _get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class CartItemCreate(BaseModel):
    product_id: str
    quantity: int


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    product_id: str
    quantity: int
    price: float
    product_name: str
    product_image: Optional[str] = None
    subtotal: float
    added_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CartResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    items: List[CartItemResponse]
    total_amount: float
    total_items: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CartSummary(BaseModel):
    total_items: int
    total_amount: float
    estimated_tax: float
    estimated_shipping: float
    estimated_total: float


class CheckoutRequest(BaseModel):
    shipping_address: Dict
    billing_address: Dict
    payment_method: str


# Helper functions
async def get_product_details(product_id: str) -> Optional[Dict]:
    """Get product details from product service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except httpx.RequestError:
            return None


async def check_product_availability(product_id: str, quantity: int) -> bool:
    """Check if product is available in requested quantity"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}/stock")
            if response.status_code == 200:
                stock_info = response.json()
                return stock_info["stock_quantity"] >= quantity
            return False
        except httpx.RequestError:
            return False


async def get_or_create_cart(user_id: str) -> Dict:
    """Get existing cart or create new one"""
    cart = await carts_collection.find_one({"user_id": user_id})

    if not cart:
        # Create new cart
        cart_data = {
            "user_id": user_id,
            "items": [],
            "total_amount": 0.0,
            "total_items": 0,
            "created_at": datetime.datetime.now(datetime.UTC),
            "updated_at": datetime.datetime.now(datetime.UTC),
            "expires_at": datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)  # Cart expires in 30 days
        }
        result = await carts_collection.insert_one(cart_data)
        cart = await carts_collection.find_one({"_id": result.inserted_id})

    return cart


async def calculate_cart_totals(cart_id: ObjectId) -> Dict:
    """Calculate cart totals"""
    pipeline = [
        {"$match": {"cart_id": cart_id}},
        {"$group": {
            "_id": None,
            "total_items": {"$sum": "$quantity"},
            "total_amount": {"$sum": "$subtotal"}
        }}
    ]

    result = await cart_items_collection.aggregate(pipeline).to_list(1)
    if result:
        return {
            "total_items": result[0]["total_items"],
            "total_amount": result[0]["total_amount"]
        }
    return {"total_items": 0, "total_amount": 0.0}


async def update_cart_totals(cart_id: ObjectId):
    """Update cart totals"""
    totals = await calculate_cart_totals(cart_id)
    await carts_collection.update_one(
        {"_id": cart_id},
        {
            "$set": {
                "total_items": totals["total_items"],
                "total_amount": totals["total_amount"],
                "updated_at": datetime.datetime.now(datetime.UTC)
            }
        }
    )


async def cleanup_expired_carts():
    """Clean up expired carts"""
    current_time = datetime.datetime.now(datetime.UTC)
    expired_carts = await carts_collection.find(
        {"expires_at": {"$lt": current_time}}
    ).to_list(None)

    for cart in expired_carts:
        # Remove cart items
        await cart_items_collection.delete_many({"cart_id": cart["_id"]})
        # Remove cart
        await carts_collection.delete_one({"_id": cart["_id"]})


# Routes
@app.post("/carts/{user_id}/items", response_model=CartItemResponse)
async def add_item_to_cart(user_id: str, item: CartItemCreate):
    # Validate product exists and get details
    product = await get_product_details(item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check availability
    if not await check_product_availability(item.product_id, item.quantity):
        raise HTTPException(status_code=400, detail="Product not available in requested quantity")

    # Get or create cart
    cart = await get_or_create_cart(user_id)

    # Check if item already exists in cart
    existing_item = await cart_items_collection.find_one({
        "cart_id": cart["_id"],
        "product_id": item.product_id
    })

    if existing_item:
        # Update quantity
        new_quantity = existing_item["quantity"] + item.quantity

        # Check availability for new quantity
        if not await check_product_availability(item.product_id, new_quantity):
            raise HTTPException(status_code=400, detail="Not enough stock available")

        updated_item = await cart_items_collection.find_one_and_update(
            {"_id": existing_item["_id"]},
            {
                "$set": {
                    "quantity": new_quantity,
                    "subtotal": product["price"] * new_quantity,
                    "updated_at": datetime.datetime.now(datetime.UTC)
                }
            },
            return_document=True
        )

        await update_cart_totals(cart["_id"])
        return updated_item

    else:
        # Add new item
        cart_item = {
            "cart_id": cart["_id"],
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": product["price"],
            "product_name": product["name"],
            "product_image": product["images"][0] if product["images"] else None,
            "subtotal": product["price"] * item.quantity,
            "added_at": datetime.datetime.now(datetime.UTC),
            "updated_at": datetime.datetime.now(datetime.UTC)
        }

        result = await cart_items_collection.insert_one(cart_item)
        created_item = await cart_items_collection.find_one({"_id": result.inserted_id})

        await update_cart_totals(cart["_id"])
        return created_item


@app.get("/carts/{user_id}", response_model=CartResponse)
async def get_cart(user_id: str):
    cart = await get_or_create_cart(user_id)

    # Get cart items
    items = await cart_items_collection.find({"cart_id": cart["_id"]}).to_list(None)

    # Update cart with items
    cart["items"] = items

    return cart


@app.put("/carts/{user_id}/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(user_id: str, item_id: str, item_update: CartItemUpdate):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid item ID")

    # Find cart item
    cart_item = await cart_items_collection.find_one({"_id": ObjectId(item_id)})
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Verify cart belongs to user
    cart = await carts_collection.find_one({"_id": cart_item["cart_id"]})
    if not cart or cart["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check availability
    if not await check_product_availability(cart_item["product_id"], item_update.quantity):
        raise HTTPException(status_code=400, detail="Product not available in requested quantity")

    # Update item
    updated_item = await cart_items_collection.find_one_and_update(
        {"_id": ObjectId(item_id)},
        {
            "$set": {
                "quantity": item_update.quantity,
                "subtotal": cart_item["price"] * item_update.quantity,
                "updated_at": datetime.datetime.now(datetime.UTC)
            }
        },
        return_document=True
    )

    await update_cart_totals(cart["_id"])
    return updated_item


@app.delete("/carts/{user_id}/items/{item_id}")
async def remove_cart_item(user_id: str, item_id: str):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid item ID")

    # Find cart item
    cart_item = await cart_items_collection.find_one({"_id": ObjectId(item_id)})
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Verify cart belongs to user
    cart = await carts_collection.find_one({"_id": cart_item["cart_id"]})
    if not cart or cart["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Remove item
    await cart_items_collection.delete_one({"_id": ObjectId(item_id)})
    await update_cart_totals(cart["_id"])

    return {"message": "Item removed from cart"}


@app.delete("/carts/{user_id}")
async def clear_cart(user_id: str):
    cart = await carts_collection.find_one({"user_id": user_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Remove all items
    await cart_items_collection.delete_many({"cart_id": cart["_id"]})

    # Update cart totals
    await carts_collection.update_one(
        {"_id": cart["_id"]},
        {
            "$set": {
                "total_items": 0,
                "total_amount": 0.0,
                "updated_at": datetime.datetime.now(datetime.UTC)
            }
        }
    )

    return {"message": "Cart cleared"}


@app.get("/carts/{user_id}/summary", response_model=CartSummary)
async def get_cart_summary(user_id: str):
    cart = await get_or_create_cart(user_id)
    totals = await calculate_cart_totals(cart["_id"])
    estimated_tax = round(totals["total_amount"] * 0.07, 2)  # Example: 7% tax
    estimated_shipping = 5.0 if totals["total_items"] > 0 else 0.0  # Flat shipping rate
    estimated_total = round(totals["total_amount"] + estimated_tax + estimated_shipping, 2)
    return CartSummary(
        total_items=totals["total_items"],
        total_amount=totals["total_amount"],
        estimated_tax=estimated_tax,
        estimated_shipping=estimated_shipping,
        estimated_total=estimated_total
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
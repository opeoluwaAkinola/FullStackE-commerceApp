# Product Catalog Microservice
# File: product_service/main.py

from fastapi import FastAPI, HTTPException, Depends, Query
from pymongo import AsyncMongoClient
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
from bson import ObjectId
import os

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

client = AsyncMongoClient(MONGODB_URL)
database = client.ecommerce
products_collection = database.products
categories_collection = database.categories

app = FastAPI(title="Product Catalog Service", version="1.0.0")


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
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    sku: str
    stock_quantity: int
    images: List[str] = []
    specifications: dict = {}
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    stock_quantity: Optional[int] = None
    images: Optional[List[str]] = None
    specifications: Optional[dict] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: str
    price: float
    category_id: str
    sku: str
    stock_quantity: int
    images: List[str]
    specifications: dict
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CategoryCreate(BaseModel):
    name: str
    description: str
    parent_id: Optional[str] = None
    slug: Optional[str] = None  # Optional slug for SEO purposes


class CategoryResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: str
    parent_id: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class InventoryUpdate(BaseModel):
    stock_quantity: int
    operation: str  # "add", "subtract", "set"


# Categories endpoints
@app.post("/categories", response_model=CategoryResponse)
async def create_category(category: CategoryCreate):
    category_dict = category.dict()
    category_dict["created_at"] = datetime.datetime.now(datetime.UTC)

    result = await categories_collection.insert_one(category_dict)
    created_category = await categories_collection.find_one({"_id": result.inserted_id})
    return created_category


@app.get("/categories", response_model=List[CategoryResponse])
async def get_categories():
    categories = await categories_collection.find().to_list(100)
    return categories


@app.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str):
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=400, detail="Invalid category ID")

    category = await categories_collection.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# Products endpoints
@app.post("/products", response_model=ProductResponse)
async def create_product(product: ProductCreate):
    # Check if category exists
    category = await categories_collection.find_one({"name": ObjectId(product.category)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if SKU already exists
    existing_product = await products_collection.find_one({"sku": product.sku})
    if existing_product:
        raise HTTPException(status_code=400, detail="SKU already exists")

    product_dict = product.dict()
    product_dict["created_at"] = datetime.datetime.now(datetime.UTC)
    product_dict["updated_at"] = datetime.datetime.now(datetime.UTC)

    result = await products_collection.insert_one(product_dict)
    created_product = await products_collection.find_one({"_id": result.inserted_id})
    return created_product


@app.get("/products", response_model=List[ProductResponse])
async def get_products(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock: Optional[bool] = None
):

    query: dict = {"is_active": True}

    if category_id:
        if ObjectId.is_valid(category_id):
            query["category_id"] = category_id

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price
        query["price"] = price_query

    if in_stock is not None:
        if in_stock:
            query["stock_quantity"] = {"$gt": 0}
        else:
            query["stock_quantity"] = {"$lte": 0}

    products = await products_collection.find(query).skip(skip).limit(limit).to_list(limit)
    return products


@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, product_update: ProductUpdate):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")

    update_data = {k: v for k, v in product_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    update_data["updated_at"] = datetime.datetime.now(datetime.UTC)

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    updated_product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return updated_product


@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"is_active": False, "updated_at": datetime.datetime.now(datetime.UTC)}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted successfully"}


@app.patch("/products/{product_id}/inventory", response_model=ProductResponse)
async def update_inventory(product_id: str, inventory_update: InventoryUpdate):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    current_stock = product.get("stock_quantity", 0)

    if inventory_update.operation == "add":
        new_stock = current_stock + inventory_update.stock_quantity
    elif inventory_update.operation == "subtract":
        new_stock = max(0, current_stock - inventory_update.stock_quantity)
    elif inventory_update.operation == "set":
        new_stock = inventory_update.stock_quantity
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"stock_quantity": new_stock, "updated_at": datetime.datetime.now(datetime.UTC)}}
    )

    updated_product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return updated_product


@app.get("/products/{product_id}/stock")
async def check_stock(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "product_id": product_id,
        "stock_quantity": product.get("stock_quantity", 0),
        "in_stock": product.get("stock_quantity", 0) > 0
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "product-catalog"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
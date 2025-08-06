from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pymongo import AsyncMongoClient
import asyncpg
import os

app = FastAPI()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
mongo_client = AsyncMongoClient(MONGO_URI)
mongo_db = mongo_client.ecommerce


# PostgreSQL connection
POSTGRES_DSN = os.getenv("POSTGRES_DSN")

async def get_postgres_conn():
    return await asyncpg.connect(POSTGRES_DSN)

# Pydantic models
class InventoryItem(BaseModel):
    product_id: str
    stock: int
    location: Optional[str] = None

class ReserveRequest(BaseModel):
    product_id: str
    quantity: int

@app.get("/inventory/{product_id}")
async def get_stock_level(product_id: str):
    item = await mongo_db.inventory.find_one({"product_id": product_id})
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product_id": product_id, "stock": item["stock"]}

@app.put("/inventory/{product_id}")
async def update_stock(product_id: str, data: InventoryItem):
    result = await mongo_db.inventory.update_one({"product_id": product_id}, {"$set": data.dict()}, upsert=True)
    return {"updated": result.modified_count > 0 or result.upserted_id is not None}

@app.post("/inventory/reserve")
async def reserve_items(req: ReserveRequest):
    item = await mongo_db.inventory.find_one({"product_id": req.product_id})
    if not item or item["stock"] < req.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    await mongo_db.inventory.update_one({"product_id": req.product_id}, {"$inc": {"stock": -req.quantity}})
    # Optionally, log reservation in PostgreSQL
    conn = await get_postgres_conn()
    await conn.execute("INSERT INTO reservations (product_id, quantity) VALUES ($1, $2)", req.product_id, req.quantity)
    await conn.close()
    return {"reserved": True} 

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
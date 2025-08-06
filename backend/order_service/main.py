# Order Management Microservice
# File: order_service/main.py

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
from enum import Enum
import os
import httpx
import asyncio

# Database setup
DATABASE_URL = os.getenv("POSTGRES_DSN")
print(f"Connecting to database at {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Service URLs
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8004")


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Database Models
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    order_number = Column(String, unique=True, index=True)
    status = Column(String, default=OrderStatus.PENDING)
    total_amount = Column(Float)
    shipping_address = Column(JSON)
    billing_address = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC), onupdate=datetime.datetime.now(datetime.UTC))

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(String)
    quantity = Column(Integer)
    price = Column(Float)

    order = relationship("Order", back_populates="items")


Base.metadata.create_all(bind=engine)


# Pydantic models
class AddressModel(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int


class OrderItemResponse(BaseModel):
    id: int
    product_id: str
    quantity: int
    price: float


class OrderCreate(BaseModel):
    user_id: str
    items: List[OrderItemCreate]
    shipping_address: AddressModel
    billing_address: AddressModel


class OrderResponse(BaseModel):
    id: int
    user_id: str
    order_number: str
    status: OrderStatus
    total_amount: float
    shipping_address: AddressModel
    billing_address: AddressModel
    items: List[OrderItemResponse]
    created_at: datetime.datetime
    updated_at: datetime.datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


app = FastAPI(title="Order Management Service", version="1.0.0")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper functions
async def get_product_price(product_id: str) -> float:
    """Get product price from product service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
            if response.status_code == 200:
                product = response.json()
                return product["price"]
            else:
                raise HTTPException(status_code=404, detail="Product not found")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Product service unavailable")


async def check_product_stock(product_id: str, quantity: int) -> bool:
    """Check if product has sufficient stock"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}/stock")
            if response.status_code == 200:
                stock_info = response.json()
                return stock_info["stock_quantity"] >= quantity
            else:
                return False
        except httpx.RequestError:
            return False


async def update_product_stock(product_id: str, quantity: int, operation: str = "subtract"):
    """Update product stock after order"""
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "stock_quantity": quantity,
                "operation": operation
            }
            response = await client.patch(
                f"{PRODUCT_SERVICE_URL}/products/{product_id}/inventory",
                json=payload
            )
            return response.status_code == 200
        except httpx.RequestError:
            return False


def generate_order_number() -> str:
    """Generate unique order number"""
    import uuid
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


async def notify_payment_service(order_id: int, amount: float):
    """Notify payment service about new order"""
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "order_id": order_id,
                "amount": amount,
                "currency": "USD"
            }
            response = await client.post(
                f"{PAYMENT_SERVICE_URL}/process-payment",
                json=payload
            )
            return response.status_code == 200
        except httpx.RequestError:
            return False


# Routes
@app.post("/orders", response_model=OrderResponse)
async def create_order(order: OrderCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Validate stock for all items
    for item in order.items:
        stock_available = await check_product_stock(item.product_id, item.quantity)
        if not stock_available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product {item.product_id}"
            )

    # Calculate total amount
    total_amount = 0
    order_items_data = []

    for item in order.items:
        price = await get_product_price(item.product_id)
        item_total = price * item.quantity
        total_amount += item_total

        order_items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": price
        })

    # Create order
    db_order = Order(
        user_id=order.user_id,
        order_number=generate_order_number(),
        total_amount=total_amount,
        shipping_address=order.shipping_address.dict(),
        billing_address=order.billing_address.dict()
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Create order items
    for item_data in order_items_data:
        db_item = OrderItem(
            order_id=db_order.id,
            **item_data
        )
        db.add(db_item)

    db.commit()

    # Update stock in background
    for item in order.items:
        background_tasks.add_task(update_product_stock, item.product_id, item.quantity)

    # Notify payment service
    background_tasks.add_task(notify_payment_service, db_order.id, total_amount)

    # Get complete order with items
    db.refresh(db_order)
    return db_order


@app.get("/orders", response_model=List[OrderResponse])
async def get_orders(
        skip: int = 0,
        limit: int = 10,
        user_id: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        db: Session = Depends(get_db)
):
    query = db.query(Order)

    if user_id:
        query = query.filter(Order.user_id == user_id)

    if status:
        query = query.filter(Order.status == status)

    orders = query.offset(skip).limit(limit).all()
    return orders


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
        order_id: int,
        status_update: OrderStatusUpdate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Handle cancellation - restore stock
    if status_update.status == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
        for item in order.items:
            background_tasks.add_task(update_product_stock, item.product_id, item.quantity, "add")

    order.status = status_update.status
    order.updated_at = datetime.datetime.now(datetime.UTC)
    db.commit()
    db.refresh(order)

    return order


@app.get("/orders/{order_id}/status")
async def get_order_status(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order_id,
        "status": order.status,
        "order_number": order.order_number,
        "updated_at": order.updated_at
    }


@app.delete("/orders/{order_id}")
async def cancel_order(
        order_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel shipped or delivered orders"
        )

    # Restore stock
    for item in order.items:
        background_tasks.add_task(update_product_stock, item.product_id, item.quantity, "add")

    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.datetime.now(datetime.UTC)
    db.commit()

    return {"message": "Order cancelled successfully"}


@app.get("/users/{user_id}/orders", response_model=List[OrderResponse])
async def get_user_orders(
        user_id: str,
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(Order.user_id == user_id).offset(skip).limit(limit).all()
    return orders


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "order-management"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
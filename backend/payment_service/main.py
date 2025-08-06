# Payment Processing Microservice
# File: payment_service/main.py

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import datetime
from enum import Enum
import os
import httpx
import uuid
import hashlib
import hmac

# Database setup
DATABASE_URL = os.getenv("POSTGRES_DSN")
print(f"Connecting to database at {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Service URLs
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8005")


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    BANK_TRANSFER = "bank_transfer"


# Database Models
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True, index=True)
    order_id = Column(Integer, index=True)
    user_id = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String, default="USD")
    payment_method = Column(String)
    status = Column(String, default=PaymentStatus.PENDING)
    gateway_transaction_id = Column(String)
    gateway_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC), onupdate=datetime.datetime.now(datetime.UTC))
    processed_at = Column(DateTime, nullable=True)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    method_type = Column(String)
    provider = Column(String)
    token = Column(String)  # Tokenized payment method
    last_four = Column(String)
    expiry_month = Column(Integer)
    expiry_year = Column(Integer)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    refund_id = Column(String, unique=True, index=True)
    payment_id = Column(String, index=True)
    amount = Column(Float)
    reason = Column(String)
    status = Column(String, default=PaymentStatus.PENDING)
    gateway_refund_id = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    processed_at = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)


# Pydantic models
class PaymentCreate(BaseModel):
    order_id: int
    user_id: str
    amount: float
    currency: str = "USD"
    payment_method: str
    payment_details: Dict = {}


class PaymentResponse(BaseModel):
    id: int
    payment_id: str
    order_id: int
    user_id: str
    amount: float
    currency: str
    payment_method: str
    status: PaymentStatus
    gateway_transaction_id: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    processed_at: Optional[datetime.datetime]


class PaymentMethodCreate(BaseModel):
    user_id: str
    method_type: str
    provider: str
    card_number: str
    expiry_month: int
    expiry_year: int
    cvv: str
    cardholder_name: str


class PaymentMethodResponse(BaseModel):
    id: int
    user_id: str
    method_type: str
    provider: str
    last_four: str
    expiry_month: int
    expiry_year: int
    is_default: bool
    is_active: bool
    created_at: datetime.datetime


class RefundCreate(BaseModel):
    payment_id: str
    amount: Optional[float] = None  # None for full refund
    reason: str


class RefundResponse(BaseModel):
    id: int
    refund_id: str
    payment_id: str
    amount: float
    reason: str
    status: PaymentStatus
    created_at: datetime.datetime
    processed_at: Optional[datetime.datetime]


class WebhookPayload(BaseModel):
    event_type: str
    data: Dict


app = FastAPI(title="Payment Processing Service", version="1.0.0")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Payment Gateway Simulators
class PaymentGateway:
    @staticmethod
    async def process_payment(payment_data: dict) -> dict:
        """Simulate payment processing"""
        # Simulate different scenarios based on amount
        amount = payment_data.get("amount", 0)

        if amount > 10000:  # Simulate failure for large amounts
            return {
                "success": False,
                "transaction_id": None,
                "error": "Payment declined - amount too high",
                "gateway_response": {"code": "DECLINED", "message": "Amount exceeds limit"}
            }

        # Simulate successful payment
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "transaction_id": transaction_id,
            "error": None,
            "gateway_response": {
                "code": "SUCCESS",
                "message": "Payment processed successfully",
                "transaction_id": transaction_id
            }
        }

    @staticmethod
    async def process_refund(refund_data: dict) -> dict:
        """Simulate refund processing"""
        refund_id = f"rfnd_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "refund_id": refund_id,
            "error": None,
            "gateway_response": {
                "code": "SUCCESS",
                "message": "Refund processed successfully",
                "refund_id": refund_id
            }
        }


def generate_payment_id() -> str:
    """Generate unique payment ID"""
    return f"PAY-{uuid.uuid4().hex[:8].upper()}"


def generate_refund_id() -> str:
    """Generate unique refund ID"""
    return f"REF-{uuid.uuid4().hex[:8].upper()}"


def tokenize_card(card_number: str) -> str:
    """Tokenize card number for security"""
    # Simple tokenization - in production, use proper PCI DSS compliant tokenization
    return hashlib.sha256(card_number.encode()).hexdigest()[:16]


async def notify_order_service(order_id: int, payment_status: str):
    """Notify order service about payment status"""
    async with httpx.AsyncClient() as client:
        try:
            status_map = {
                "completed": "confirmed",
                "failed": "cancelled",
                "cancelled": "cancelled"
            }

            if payment_status in status_map:
                payload = {"status": status_map[payment_status]}
                response = await client.put(
                    f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
                    json=payload
                )
                return response.status_code == 200
        except httpx.RequestError:
            return False


# Routes
@app.post("/payments", response_model=PaymentResponse)
async def create_payment(
        payment: PaymentCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    # Create payment record
    payment_id = generate_payment_id()
    db_payment = Payment(
        payment_id=payment_id,
        order_id=payment.order_id,
        user_id=payment.user_id,
        amount=payment.amount,
        currency=payment.currency,
        payment_method=payment.payment_method,
        status=PaymentStatus.PROCESSING
    )

    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)

    # Process payment asynchronously
    background_tasks.add_task(
        process_payment_async,
        db_payment.id,
        payment.payment_details
    )

    return db_payment


async def process_payment_async(payment_id: int, payment_details: dict):
    """Process payment asynchronously"""
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return

        # Process with gateway
        gateway_result = await PaymentGateway.process_payment({
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            **payment_details
        })

        # Update payment status
        if gateway_result["success"]:
            payment.status = PaymentStatus.COMPLETED
            payment.gateway_transaction_id = gateway_result["transaction_id"]
            payment.processed_at = datetime.datetime.now(datetime.UTC)

            # Notify order service
            await notify_order_service(payment.order_id, "completed")
        else:
            payment.status = PaymentStatus.FAILED

            # Notify order service
            await notify_order_service(payment.order_id, "failed")

        payment.gateway_response = gateway_result["gateway_response"]
        payment.updated_at = datetime.datetime.now(datetime.UTC)

        db.commit()

    finally:
        db.close()


@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.get("/payments", response_model=List[PaymentResponse])
async def get_payments(
        skip: int = 0,
        limit: int = 10,
        user_id: Optional[str] = None,
        order_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
        db: Session = Depends(get_db)
):
    query = db.query(Payment)

    if user_id:
        query = query.filter(Payment.user_id == user_id)

    if order_id:
        query = query.filter(Payment.order_id == order_id)

    if status:
        query = query.filter(Payment.status == status)

    payments = query.offset(skip).limit(limit).all()
    return payments


@app.post("/payment-methods", response_model=PaymentMethodResponse)
async def add_payment_method(payment_method: PaymentMethodCreate, db: Session = Depends(get_db)):
    # Tokenize card number
    token = tokenize_card(payment_method.card_number)
    last_four = payment_method.card_number[-4:]

    # Check if this is the first payment method for the user
    existing_methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == payment_method.user_id,
        PaymentMethod.is_active == True
    ).count()

    is_default = existing_methods == 0

    db_payment_method = PaymentMethod(
        user_id=payment_method.user_id,
        method_type=payment_method.method_type,
        provider=payment_method.provider,
        token=token,
        last_four=last_four,
        expiry_month=payment_method.expiry_month,
        expiry_year=payment_method.expiry_year,
        is_default=is_default
    )

    db.add(db_payment_method)
    db.commit()
    db.refresh(db_payment_method)

    return db_payment_method


@app.get("/users/{user_id}/payment-methods", response_model=List[PaymentMethodResponse])
async def get_user_payment_methods(user_id: str, db: Session = Depends(get_db)):
    methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == user_id,
        PaymentMethod.is_active == True
    ).all()
    return methods


@app.post("/refunds", response_model=RefundResponse)
async def create_refund(
        refund: RefundCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    # Find original payment
    payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status != PaymentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Payment not completed")

    # Determine refund amount
    refund_amount = refund.amount if refund.amount else payment.amount

    if refund_amount > payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

    # Create refund record
    refund_id = generate_refund_id()
    db_refund = Refund(
        refund_id=refund_id,
        payment_id=refund.payment_id,
        amount=refund_amount,
        reason=refund.reason,
        status=PaymentStatus.PROCESSING
    )

    db.add(db_refund)
    db.commit()
    db.refresh(db_refund)

    # Process refund asynchronously
    background_tasks.add_task(process_refund_async, db_refund.id)

    return db_refund


async def process_refund_async(refund_id: int):
    """Process refund asynchronously"""
    db = SessionLocal()
    try:
        refund = db.query(Refund).filter(Refund.id == refund_id).first()
        if not refund:
            return

        # Process with gateway
        gateway_result = await PaymentGateway.process_refund({
            "payment_id": refund.payment_id,
            "amount": refund.amount,
            "reason": refund.reason
        })

        # Update refund status
        if gateway_result["success"]:
            refund.status = PaymentStatus.COMPLETED
            refund.gateway_refund_id = gateway_result["refund_id"]
            refund.processed_at = datetime.datetime.now(datetime.UTC)

            # Update original payment status if full refund
            payment = db.query(Payment).filter(Payment.payment_id == refund.payment_id).first()
            if payment and refund.amount == payment.amount:
                payment.status = PaymentStatus.REFUNDED
                payment.updated_at = datetime.datetime.now(datetime.UTC)
        else:
            refund.status = PaymentStatus.FAILED

        db.commit()

    finally:
        db.close()


@app.get("/refunds/{refund_id}", response_model=RefundResponse)
async def get_refund(refund_id: str, db: Session = Depends(get_db)):
    refund = db.query(Refund).filter(Refund.refund_id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund


@app.post("/webhooks/payment")
async def payment_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    """Handle payment gateway webhooks"""
    event_type = payload.event_type
    data = payload.data

    if event_type == "payment.completed":
        # Update payment status
        transaction_id = data.get("transaction_id")
        if transaction_id:
            payment = db.query(Payment).filter(
                Payment.gateway_transaction_id == transaction_id
            ).first()
            if payment:
                payment.status = PaymentStatus.COMPLETED
                payment.processed_at = datetime.datetime.now(datetime.UTC)
                db.commit()

    elif event_type == "payment.failed":
        # Update payment status
        transaction_id = data.get("transaction_id")
        if transaction_id:
            payment = db.query(Payment).filter(
                Payment.gateway_transaction_id == transaction_id
            ).first()
            if payment:
                payment.status = PaymentStatus.FAILED
                db.commit()

    return {"status": "webhook processed"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "payment-processing"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
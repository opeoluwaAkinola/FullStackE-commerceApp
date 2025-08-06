from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import asyncpg
import os

app = FastAPI()

POSTGRES_DSN = os.getenv("POSTGRES_DSN")
async def get_postgres_conn():
    return await asyncpg.connect(POSTGRES_DSN)

class Notification(BaseModel):
    user_id: int
    message: str
    type: str  # e.g., 'email', 'sms'

@app.post("/notifications")
async def send_notification(notification: Notification):
    conn = await get_postgres_conn()
    await conn.execute(
        "INSERT INTO notifications (user_id, message, type) VALUES ($1, $2, $3)",
        notification.user_id, notification.message, notification.type
    )
    await conn.close()
    return {"sent": True}

@app.get("/notifications/{user_id}", response_model=List[Notification])
async def get_user_notifications(user_id: int):
    conn = await get_postgres_conn()
    rows = await conn.fetch("SELECT user_id, message, type FROM notifications WHERE user_id=$1", user_id)
    await conn.close()
    return [Notification(**dict(row)) for row in rows] 

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
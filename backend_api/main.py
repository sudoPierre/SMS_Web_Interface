import psycopg
import os
import secrets
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Literal
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_IDENTIFIER = os.getenv("ADMIN_IDENTIFIER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

security = HTTPBearer()


class SMSRequest(BaseModel):
    phoneNumber: str
    message: str

class SMSPayload(BaseModel):
    messageId: str
    message: str
    phoneNumber: str
    simNumber: int
    receivedAt: datetime

class SMSReceived(BaseModel):
    event: str
    payload: SMSPayload

class LoginRequest(BaseModel):
    identifier: str
    password: str


def get_db():
    return psycopg.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT
    )

def write_sms_in_db(phoneNumber: str, body: str, direction: Literal["inbound", "outbound"]):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO messages(phone_number, body, direction, status) VALUES(%s, %s, %s, %s)",
                (phoneNumber, body, direction, "pending"),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def create_token(identifier: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    return jwt.encode({"sub": identifier, "exp": expire}, SECRET_KEY, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.post("/api/auth/login")
def login(data: LoginRequest):
    if data.identifier == ADMIN_IDENTIFIER and data.password == ADMIN_PASSWORD:
        return {"token": create_token(data.identifier)}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# --- Webhook: no auth, called by the SMS gateway ---

@app.post("/webhook")
def received_sms_from_gateway(data: SMSReceived):
    try:
        write_sms_in_db(data.payload.phoneNumber, data.payload.message, "inbound")
    except Exception:
        return {"status": "error"}
    return {"status": "success", "message": "Webhook received"}


# --- SMS send ---

@app.post("/api/messages/send")
def send_sms(payload: SMSRequest, _: str = Depends(verify_token)):
    try:
        write_sms_in_db(payload.phoneNumber, payload.message, "outbound")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "SMS ready for processing.", "phoneNumber": payload.phoneNumber}


# --- Read endpoints ---

@app.get("/api/conversations")
def get_conversations(_: str = Depends(verify_token)):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT ON (phone_number)
                    phone_number, body, direction, status, created_at
                FROM messages
                ORDER BY phone_number, created_at DESC
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()
    return [
        {
            "phone_number": r[0],
            "last_message": r[1],
            "direction": r[2],
            "status": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]

@app.get("/api/conversations/{phone_number}")
def get_conversation_messages(phone_number: str, _: str = Depends(verify_token)):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, body, direction, status, created_at
                FROM messages
                WHERE phone_number = %s
                ORDER BY created_at ASC
            """, (phone_number,))
            rows = cursor.fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "body": r[1],
            "direction": r[2],
            "status": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]

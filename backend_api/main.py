import psycopg
import os
import secrets
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Literal
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_IDENTIFIER = os.getenv("ADMIN_IDENTIFIER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


def get_db():
    return psycopg.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT
    )

def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    phone_number VARCHAR(20) NOT NULL,
                    body TEXT NOT NULL,
                    direction VARCHAR(10) CHECK (direction IN ('inbound', 'outbound')),
                    status VARCHAR(20) DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    phone_number VARCHAR(20) UNIQUE NOT NULL,
                    activated BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE OR REPLACE FUNCTION create_user_if_not_exists()
                RETURNS trigger AS $$
                DECLARE exists_in_users BOOLEAN;
                BEGIN
                    SELECT EXISTS (SELECT 1 FROM users WHERE phone_number = NEW.phone_number)
                    INTO exists_in_users;
                    IF NOT exists_in_users THEN
                        INSERT INTO users (phone_number) VALUES (NEW.phone_number);
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                DROP TRIGGER IF EXISTS trigger_on_messages_insert ON messages;
                CREATE TRIGGER trigger_on_messages_insert
                    AFTER INSERT ON messages FOR EACH ROW
                    EXECUTE FUNCTION create_user_if_not_exists();
                CREATE OR REPLACE FUNCTION notify_worker()
                RETURNS trigger AS $$
                BEGIN
                    IF NEW.status = 'pending' AND NEW.direction = 'outbound' THEN
                        PERFORM pg_notify('worker_channel', NEW.id::text);
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                DROP TRIGGER IF EXISTS trigger_notify_worker_on_pending_message ON messages;
                CREATE TRIGGER trigger_notify_worker_on_pending_message
                    AFTER INSERT ON messages FOR EACH ROW
                    EXECUTE FUNCTION notify_worker();
            """)
        conn.commit()
        logger.info("Database schema ready")
    except Exception as e:
        conn.rollback()
        logger.error("Failed to initialize schema: %s", e)
        raise
    finally:
        conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# --- Models ---

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


# --- Helpers ---

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


# --- Auth ---

@app.post("/api/auth/login")
def login(data: LoginRequest):
    if data.identifier == ADMIN_IDENTIFIER and data.password == ADMIN_PASSWORD:
        return {"token": create_token(data.identifier)}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# --- Webhook: no auth, called by the SMS gateway ---

@app.post("/webhook")
async def received_sms_from_gateway(request: Request):
    body = await request.json()
    logger.info("[webhook] received: %s", body)
    try:
        data = SMSReceived(**body)
        write_sms_in_db(data.payload.phoneNumber, data.payload.message, "inbound")
    except Exception as e:
        logger.error("[webhook] failed to process: %s", e)
        return {"status": "error", "detail": str(e)}
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

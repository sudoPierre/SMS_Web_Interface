import asyncio
import psycopg
import os
import secrets
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

import agent
import commands

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
                CREATE TABLE IF NOT EXISTS authorized_numbers (
                    phone_number VARCHAR(20) PRIMARY KEY,
                    label VARCHAR(100),
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
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
        apply_migrations(conn)
        logger.info("Database schema ready")
    except Exception as e:
        conn.rollback()
        logger.error("Failed to initialize schema: %s", e)
        raise
    finally:
        conn.close()

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def apply_migrations(conn):
    """Run each migrations/*.sql file once, in name order, each in its own transaction."""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("SELECT version FROM schema_migrations")
        applied = {r[0] for r in cursor.fetchall()}
    conn.commit()
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in applied:
            continue
        with conn.cursor() as cursor:
            cursor.execute(path.read_text())
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
        conn.commit()
        logger.info("Applied migration %s", path.name)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    commands.load_commands()
    agent.load_tools()
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

class AuthorizedNumberCreate(BaseModel):
    phone_number: str
    label: Optional[str] = None

class AuthorizedNumberUpdate(BaseModel):
    label: Optional[str] = None
    enabled: Optional[bool] = None
    agent_enabled: Optional[bool] = None
    is_admin: Optional[bool] = None

class LoginRequest(BaseModel):
    identifier: str
    password: str


# --- Helpers ---

SenderType = Literal["human", "command", "ai_agent"]

def write_sms_in_db(
    phoneNumber: str,
    body: str,
    direction: Literal["inbound", "outbound"],
    sender_type: SenderType = "human",
):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO messages(phone_number, body, direction, status, sender_type) VALUES(%s, %s, %s, %s, %s)",
                (phoneNumber, body, direction, "pending", sender_type),
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

def should_handle(text: str) -> bool:
    """Whether an incoming SMS goes to the command engine or the AI agent."""
    return commands.is_command(text) or agent.is_enabled()

async def handle_incoming_sms(sender: str, text: str):
    """Route an SMS from the gateway: "/..." to the command engine, anything else to the AI agent.

    Both paths check the whitelist before doing anything. The agent only answers numbers
    from the authorized_numbers table (not AUTHORIZED_NUMBERS), so it can be granted per number.
    """
    if commands.is_command(text):
        if not await asyncio.to_thread(commands.is_authorized, sender, get_db):
            logger.warning("[commands] ignored command from unauthorized number %s", sender)
            return
        await commands.dispatch(
            sender, text,
            reply=lambda message: write_sms_in_db(sender, message, "outbound", "command"),
            get_db=get_db,
        )
        return

    if not agent.is_enabled():
        return
    if not await asyncio.to_thread(commands.is_authorized, sender, get_db, False, True):
        logger.info("[agent] ignored SMS from %s: not whitelisted or AI agent disabled", sender)
        return
    reply = await agent.run_agent(sender, text)
    await asyncio.to_thread(write_sms_in_db, sender, reply, "outbound", "ai_agent")

@app.post("/webhook")
async def received_sms_from_gateway(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    logger.info("[webhook] received: %s", body)
    try:
        data = SMSReceived(**body)
        write_sms_in_db(data.payload.phoneNumber, data.payload.message, "inbound")
    except Exception as e:
        logger.error("[webhook] failed to process: %s", e)
        return {"status": "error", "detail": str(e)}
    # Commands and the agent run after the response is sent, so the gateway never waits on external APIs
    if data.event == "sms:received" and should_handle(data.payload.message):
        background_tasks.add_task(handle_incoming_sms, data.payload.phoneNumber, data.payload.message)
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
                    phone_number, body, direction, status, created_at, sender_type
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
            "sender_type": r[5],
        }
        for r in rows
    ]

@app.get("/api/conversations/{phone_number}")
def get_conversation_messages(phone_number: str, _: str = Depends(verify_token)):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, body, direction, status, created_at, sender_type
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
            "sender_type": r[5],
        }
        for r in rows
    ]


# --- SMS command whitelist ---

def authorized_number_row(r):
    return {
        "phone_number": r[0],
        "label": r[1],
        "enabled": r[2],
        "created_at": r[3].isoformat() if r[3] else None,
        "agent_enabled": r[4],
        "is_admin": r[5],
        "source": "db",
    }

def valid_phone_number(number: str) -> str:
    n = commands.normalize_number(number)
    if not commands.is_valid_number(n):
        raise HTTPException(status_code=422, detail="Invalid phone number (use E.164, e.g. +33612345678)")
    return n

@app.get("/api/authorized-numbers")
def list_authorized_numbers(_: str = Depends(verify_token)):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT phone_number, label, enabled, created_at, agent_enabled, is_admin
                FROM authorized_numbers
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()
    db_numbers = [authorized_number_row(r) for r in rows]
    known = {n["phone_number"] for n in db_numbers}
    # Numbers from AUTHORIZED_NUMBERS are listed read-only: they can only be changed in the deployment config
    env_numbers = [
        {"phone_number": n, "label": None, "enabled": True, "created_at": None, "agent_enabled": False, "is_admin": True, "source": "env"}
        for n in sorted(commands.env_numbers()) if n not in known
    ]
    return env_numbers + db_numbers

@app.post("/api/authorized-numbers", status_code=201)
def add_authorized_number(payload: AuthorizedNumberCreate, _: str = Depends(verify_token)):
    number = valid_phone_number(payload.phone_number)
    label = (payload.label or "").strip() or None
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO authorized_numbers (phone_number, label)
                VALUES (%s, %s)
                ON CONFLICT (phone_number) DO NOTHING
                RETURNING phone_number, label, enabled, created_at, agent_enabled, is_admin
            """, (number, label))
            row = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=409, detail="This number is already in the whitelist")
    return authorized_number_row(row)

@app.patch("/api/authorized-numbers/{phone_number}")
def update_authorized_number(phone_number: str, payload: AuthorizedNumberUpdate, _: str = Depends(verify_token)):
    fields = payload.model_dump(exclude_unset=True)
    if "label" in fields:
        fields["label"] = (fields["label"] or "").strip() or None
    for flag in ("enabled", "agent_enabled", "is_admin"):
        if flag in fields and fields[flag] is None:
            del fields[flag]
    if not fields:
        raise HTTPException(status_code=422, detail="Nothing to update")
    assignments = ", ".join(f"{column} = %s" for column in fields)
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE authorized_numbers SET {assignments}
                WHERE phone_number = %s
                RETURNING phone_number, label, enabled, created_at, agent_enabled, is_admin
                """,
                (*fields.values(), commands.normalize_number(phone_number)),
            )
            row = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Number not found in the whitelist")
    return authorized_number_row(row)

@app.delete("/api/authorized-numbers/{phone_number}", status_code=204)
def delete_authorized_number(phone_number: str, _: str = Depends(verify_token)):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM authorized_numbers WHERE phone_number = %s",
                (commands.normalize_number(phone_number),),
            )
            deleted = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Number not found in the whitelist")

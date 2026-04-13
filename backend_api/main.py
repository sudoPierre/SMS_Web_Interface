import psycopg
import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

app = FastAPI()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")


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

def write_sms_in_db(phoneNumber: str, body: str, direction: Literal["inbound", "outbound"]):
    connection = psycopg.connect(dbname=DB_NAME,
                            user=DB_USER,
                            password=DB_PASSWORD,
                            host=DB_HOST,
                            port=DB_PORT)

    try:
        with connection.cursor() as cursor:
            sql = """ INSERT INTO messages(phone_number, body, direction, status) VALUES(%s, %s, %s, %s)"""
            cursor.execute(sql, (phoneNumber, body, direction, 'pending'))

        connection.commit()
    except Exception as e:
        print (e)
        connection.rollback()
    finally:
        connection.close()

@app.post("/webhook")
def received_sms_from_gateway(data: SMSReceived):
    try:
        write_sms_in_db(data.payload.phoneNumber, data.payload.message, "inbound")
    except Exception as e:
        return
    return {"status": "success", "message": "Webhook received"}

@app.post("/api/messages/send")
def sent_sms_from_front(payload: SMSRequest):
    try:
        write_sms_in_db(payload.phoneNumber, payload.message, "outbound")
    except Exception as e:
        return {"status": "Failed", "phoneNumber": payload.phoneNumber, "Error": str(e)}
    return {"status": "SMS ready for processing.", "phoneNumber": payload.phoneNumber}
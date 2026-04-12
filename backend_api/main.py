import pymysql.cursors
import os
import cryptography
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

app = FastAPI()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

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

def write_sms_in_db(phone_number: str, body: str, direction: Literal["inbound", "outbound"]):
    connection = pymysql.connect(host=DB_HOST,
                                user=DB_USER,
                                password=DB_PASSWORD,
                                database=DB_NAME,
                                cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            sql = " INSERT INTO `messages`(`phone_number`, `body`, `direction`, `status`) VALUES(%s, %s, %s, %s)"
            cursor.execute(sql, (phone_number, body, direction, 'pending'))

        connection.commit()
    except Exception as e:
        print (e)
        connection.rollback()
    finally:
        connection.close()

@app.post("/webhook")
def received_sms_from_gateway(data: SMSReceived):
    write_sms_in_db(data.payload.phoneNumber, data.payload.message, "inbound")
    return {"status": "success", "message": "Webhook received"}

@app.post("/api/messages/send")
def sent_sms_from_front(payload: SMSRequest):
    write_sms_in_db(payload.phoneNumber, payload.message, "outbound")
    return {"message": "SMS ready for processing.", "phone_number": payload.phone_number}
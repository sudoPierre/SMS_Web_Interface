import psycopg
import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal
from datetime import datetime
import asyncio
from android_sms_gateway import client, domain
import time

SMS_GATEWAY_LOGIN = os.getenv('SMS_GATEWAY_LOGIN')
SMS_GATEWAY_PASSWORD = os.getenv('SMS_GATEWAY_PASSWORD')
SMS_GATEWAY_URL = f"http://{os.getenv('SMS_GATEWAY_IP')}:8080"

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

async def send_sms(phoneNumber, message):
    body = domain.Message(
        phone_numbers=[phoneNumber],
        text_message=domain.TextMessage(
            text=message,
        ),
        with_delivery_report=True,
    )
    async with client.AsyncAPIClient(login=SMS_GATEWAY_LOGIN,
                                     password=SMS_GATEWAY_PASSWORD,
                                     base_url=SMS_GATEWAY_URL) as c:
        # Send message
        state = await c.send(body)
        print(f"Message sent with ID: {state.id}")
        
        # Check status
        status = await c.get_state(state.id)
        print(f"Status: {status.state}")

def processing_sms(messageId: str):
    phoneNumber = get_number_and_body_from_id(messageId)[0]
    message = get_number_and_body_from_id(messageId)[1]
    try:
        asyncio.run(send_sms(phoneNumber, message))
    except Exception as e:
        print(e)
        return
    else:
        change_message_status_to_sent(messageId)

def get_number_and_body_from_id(messageId: str):
        conn = psycopg.connect(dbname=DB_NAME,
                                user=DB_USER,
                                password=DB_PASSWORD,
                                host=DB_HOST,
                                port=DB_PORT)

        try:
            with conn.cursor() as cursor:
                sql = """ SELECT phone_number, body from messages WHERE id = %s """
                cursor.execute(sql, (messageId,))
                user_infos = cursor.fetchone()

            conn.commit()
        except Exception as e:
            print (e)
            conn.close()
            return
        
        conn.close()
        return user_infos

def change_message_status_to_sent(messageId):
    conn = psycopg.connect(dbname=DB_NAME,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        host=DB_HOST,
                        port=DB_PORT)

    try:
        with conn.cursor() as cursor:
            sql = """ UPDATE messages SET status = 'sent' WHERE id = %s"""
            cursor.execute(sql, (messageId,))

        conn.commit()
    except Exception as e:
        print (e)
        conn.close()
        return

    conn.close()
    return 

while True:
    try:
        with psycopg.connect(dbname=DB_NAME,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        host=DB_HOST,
                        port=DB_PORT,
                        autocommit=True) as conn:
            print("Connected to postgres ! listening...")
            conn.execute("LISTEN worker_channel")
            
            for notification in conn.notifies():
                print(f"Signal reçu ! Donnée : {notification.payload}")
                processing_sms(notification.payload)
                
    except (psycopg.OperationalError, Exception) as e:
        print(f"Error : {e}")
        time.sleep(5)
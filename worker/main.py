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

db_params = {
    "dbname":DB_NAME,
    "user":DB_USER,
    "password":DB_PASSWORD,
    "host":DB_HOST,
    "port":DB_PORT
}

class DatabaseManager:
    def __init__(self, db_params):
        self.params = db_params
        self.connection = None
        self.cursor = None

    def open_connection(self):
        if self.connection is None or self.connection.closed:
            try:
                self.connection = psycopg.connect( **self.params, autocommit=True)
                self.cursor = self.connection.cursor()
            except Exception as e:
                if self.connection:
                    self.connection.rollback()
                print (f" Error on open_connection class function : {e}")
    
    def close_connection(self):
        if self.connection:
            self.connection.close()

    def update(self, table, column, value, target_id):
        try:
            self.open_connection()
            with self.connection.cursor() as cursor:
                sql = f""" UPDATE {table} SET {column} = '{value}' WHERE id = %s """
                cursor.execute(sql, (target_id,))
        except Exception as e:
            print (f" Error on update class function : {e}")
            self.close_connection()
        finally:
            self.close_connection()
    
    def select(self, columns, table, target_id):
        columns_list = ", ".join(columns)
        sql = f" SELECT {columns_list} from {table} WHERE id = %s "
        try:
            self.open_connection()
            with self.connection.cursor() as cursor:
                cursor.execute(sql, (target_id,))
                results = cursor.fetchone()
        except Exception as e:
            print (f" Error on select class function : {e}")
            self.close_connection()
            return
        finally:
            self.close_connection()
        return results

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
        print (f" Error on processing_sms function : {e}")
        return
    else:
        change_message_status_to_sent(messageId)

def get_number_and_body_from_id(messageId: str):
        try:
            user_infos = db.select(columns=('phone_number', 'body'), table='messages', target_id=messageId )
        except Exception as e:
            print (f" Error on get_number_and_body_from_id function : {e}")
            return
        return user_infos

def change_message_status_to_sent(messageId):
    try:
        db.update(table='messages', column='status', value='sent', target_id=messageId)
    except Exception as e:
        print (f" Error on change_message_status_to_sent function : {e}")
    return 

db = DatabaseManager(db_params)

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
        print(f"Error on listening channel : {e}")
        time.sleep(5)
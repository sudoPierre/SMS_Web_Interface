import pymysql.cursors
import os
import cryptography

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

def write_sms_in_db(phone_number: str, body: str):
    connection = pymysql.connect(host=DB_HOST,
                                user=DB_USER,
                                password=DB_PASSWORD,
                                database=DB_NAME,
                                cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = " INSERT INTO `messages`(`phone_number`, `body`, `direction`, `status`) VALUES(%s, %s, %s, %s)"
            cursor.execute(sql, (phone_number, body, 'inbound', 'pending'))

        # connection is not autocommit by default. So you must commit to save
        # your changes.
        connection.commit()
    except Exception as e:
        print (e)
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    write_sms_in_db('+33665123456', 'this is a test message for database')
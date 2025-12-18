import os

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TOKEN")
manager_id = os.getenv("MANAGER_CHAT_ID")
PHOTO_ID = os.getenv("PHOTO_ID")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "xtmAp32?qw12!bgr8475")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///fundraising.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "static/uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Default Admin (ganti setelah production!)
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "admin123"

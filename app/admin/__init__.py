# app/admin/__init__.py
from flask import Blueprint

admin_bp = Blueprint("admin", __name__)

# Import seluruh sub-modul route
from app.admin import auth, dashboard, pages, sections
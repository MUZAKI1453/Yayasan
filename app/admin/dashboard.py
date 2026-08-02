# app/admin/dashboard.py
from flask import render_template
from flask_login import login_required
from app.admin import admin_bp
from app.models import Page

@admin_bp.route("/")
@login_required
def dashboard():
    pages = Page.query.order_by(Page.updated_at.desc()).all()
    return render_template("admin/dashboard.html", pages=pages)
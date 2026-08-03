from datetime import date
from sqlalchemy import func
from flask import render_template
from flask_login import login_required
from app.admin import admin_bp
from app.models import Page, VisitorLog


@admin_bp.route("/")
@login_required
def dashboard():
    # Ambil data halaman untuk tabel
    pages = Page.query.order_by(Page.updated_at.desc()).all()
    total_pages = len(pages)
    active_campaigns = Page.query.filter_by(is_published=True).count()

    # Hitung Statistik Pengunjung & Pageviews
    total_pengunjung = VisitorLog.query.count()

    # Hitung pageviews khusus hari ini
    today = date.today()
    pageviews_today = VisitorLog.query.filter(
        func.date(VisitorLog.timestamp) == today
    ).count()

    return render_template(
        "admin/dashboard.html",
        pages=pages,
        total_pages=total_pages,
        active_campaigns=active_campaigns,
        total_pengunjung=total_pengunjung,
        pageviews_today=pageviews_today
    )
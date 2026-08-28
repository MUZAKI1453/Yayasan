from flask import Blueprint, render_template, abort, request
from flask_login import current_user
from app.models import Page, Section, VisitorLog
from app.extensions import db

public_bp = Blueprint("public", __name__)


def log_visitor():
    """Fungsi helper untuk mencatat IP dan URL yang dikunjungi"""
    try:
        log = VisitorLog(
            ip_address=request.remote_addr,
            path=request.path
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()


@public_bp.route("/")
def index():
    # Catat statistik kunjungan di halaman utama
    log_visitor()

    # Ambil page yang paling baru dan sudah dipublish
    page = Page.query.filter_by(is_published=True).order_by(Page.updated_at.desc()).first()
    if not page:
        return render_template("public/empty.html")

    # Ambil HANYA section yang aktif dari database, diurutkan berdasarkan order
    sections = Section.query.filter_by(page_id=page.id, is_active=True).order_by(Section.order.asc()).all()

    editor_section_id = request.args.get("editor_section", type=int) if current_user.is_authenticated else None

    # Kirim variabel sections ke template
    return render_template("public/page.html", page=page, sections=sections, editor_section_id=editor_section_id)


@public_bp.route("/<slug>")
def show_page(slug):
    page = Page.query.filter_by(slug=slug, is_published=True).first_or_404()

    # Catat statistik kunjungan untuk halaman slug spesifik
    log_visitor()

    # Ambil HANYA section yang aktif dari database, diurutkan berdasarkan order
    sections = Section.query.filter_by(page_id=page.id, is_active=True).order_by(Section.order.asc()).all()

    editor_section_id = request.args.get("editor_section", type=int) if current_user.is_authenticated else None

    # Kirim variabel sections ke template
    return render_template("public/page.html", page=page, sections=sections, editor_section_id=editor_section_id)
from flask import Blueprint, render_template, abort, request
from flask_login import current_user
from app.models import Page, VisitorLog
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

    # Ambil campaign yang paling baru dan sudah dipublish
    page = Page.query.filter_by(is_published=True).order_by(Page.updated_at.desc()).first()
    if not page:
        return render_template("public/empty.html")
    editor_section_id = request.args.get("editor_section", type=int) if current_user.is_authenticated else None
    return render_template("public/page.html", page=page, editor_section_id=editor_section_id)


@public_bp.route("/<slug>")
def show_page(slug):
    page = Page.query.filter_by(slug=slug, is_published=True).first_or_404()

    # Catat statistik kunjungan untuk halaman slug spesifik
    log_visitor()

    editor_section_id = request.args.get("editor_section", type=int) if current_user.is_authenticated else None
    return render_template("public/page.html", page=page, editor_section_id=editor_section_id)
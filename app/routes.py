from flask import Blueprint, render_template, abort
from app.models import Page

public_bp = Blueprint("public", __name__)

@public_bp.route("/")
def index():
    # Ambil campaign yang paling baru dan sudah dipublish
    page = Page.query.filter_by(is_published=True).order_by(Page.updated_at.desc()).first()
    if not page:
        return render_template("public/empty.html")
    return render_template("public/page.html", page=page)

@public_bp.route("/<slug>")
def show_page(slug):
    page = Page.query.filter_by(slug=slug, is_published=True).first_or_404()
    return render_template("public/page.html", page=page)
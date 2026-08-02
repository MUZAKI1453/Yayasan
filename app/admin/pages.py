# app/admin/pages.py
import re
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required
from app.admin import admin_bp
from app.admin.templates import PRESET_TEMPLATES
from app.models import Page, Section
from app.extensions import db

@admin_bp.route('/pages')
@login_required
def list_pages():
    pages = Page.query.order_by(Page.updated_at.desc()).all()
    return render_template('admin/daftar_campaign.html', pages=pages)


@admin_bp.route("/page/new", methods=["GET", "POST"])
@login_required
def new_page():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        template_id = request.form.get("template_id", "template_ppdb")

        if not title:
            flash("Judul halaman wajib diisi!", "danger")
            return redirect(url_for("admin.new_page"))

        # Generate unique slug
        slug = re.sub(r"[^a-z0-9-]", "-", title.lower()).strip("-")
        base_slug = slug
        counter = 1

        while Page.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        page = Page(title=title, slug=slug, is_published=True)
        db.session.add(page)
        db.session.flush()

        # Generasi section dari preset template
        chosen_template = PRESET_TEMPLATES.get(template_id, PRESET_TEMPLATES["template_ppdb"])

        for idx, (s_type, s_content) in enumerate(chosen_template, start=1):
            content_copy = dict(s_content)
            if s_type == "hero" and "title" in content_copy:
                content_copy["title"] = title

            sec = Section(
                page_id=page.id,
                type=s_type,
                order=idx,
                content=content_copy
            )
            db.session.add(sec)

        db.session.commit()
        
        flash("Campaign berhasil dibuat! Silakan atur isi konten & section di bawah ini.", "success")
        
        # REVISI REDIRECT: Langsung buka Visual Editor Split-Screen
        return redirect(url_for("admin.manage_section", page_id=page.id))

    return render_template("admin/new_page.html")

@admin_bp.route("/page/<int:page_id>/toggle-publish", methods=["POST"])
@login_required
def toggle_publish(page_id):
    page = Page.query.get_or_404(page_id)
    page.is_published = not page.is_published
    db.session.commit()
    flash(f"Status diubah menjadi {'Published' if page.is_published else 'Draft'}", "success")
    return redirect(url_for("admin.list_pages"))

@admin_bp.route("/page/<int:page_id>/delete", methods=["POST"])
@login_required
def delete_page(page_id):
    page = Page.query.get_or_404(page_id)
    Section.query.filter_by(page_id=page.id).delete()
    db.session.delete(page)
    db.session.commit()
    flash(f"Halaman '{page.title}' berhasil dihapus!", "success")
    return redirect(url_for("admin.list_pages"))
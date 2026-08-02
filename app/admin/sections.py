# app/admin/sections.py
from datetime import datetime
from flask import render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required
from sqlalchemy.orm.attributes import flag_modified
from app.admin import admin_bp
from app.admin.templates import DEFAULT_SECTION_CONTENTS, save_uploaded_file
from app.models import Page, Section
from app.extensions import db

@admin_bp.route("/page/<int:page_id>/sections-manual")
@admin_bp.route("/page/<int:page_id>/manage")
@login_required
def manage_section(page_id):
    """Menampilkan Tampilan Builder Split Screen (Form Sidebar + Live Preview Iframe)"""
    page = Page.query.get_or_404(page_id)
    return render_template("admin/manage_sections.html", page=page, section=None)

@admin_bp.route("/page/<int:page_id>/add-section", methods=["POST"])
@login_required
def add_section(page_id):
    """Menambahkan Section Baru dan Tetap Berada di Halaman Builder Utama"""
    page = Page.query.get_or_404(page_id)
    section_type = request.form.get("type")

    if not section_type:
        flash("Jenis section wajib dipilih!", "danger")
        return redirect(url_for("admin.manage_section", page_id=page.id))

    last_order = db.session.query(db.func.max(Section.order)).filter_by(page_id=page.id).scalar() or 0
    initial_content = DEFAULT_SECTION_CONTENTS.get(section_type, {"title": section_type.replace('_', ' ').title()})

    section = Section(
        page_id=page.id,
        type=section_type,
        order=last_order + 1,
        content=initial_content
    )
    db.session.add(section)
    db.session.commit()

    flash(f"Section '{section_type}' berhasil ditambahkan!", "success")
    
    # REVISI: Langsung kembali ke daftar section tanpa berpindah ke form edit
    return redirect(url_for("admin.manage_section", page_id=page.id))

@admin_bp.route("/section/<int:section_id>/edit", methods=["GET", "POST"])
@login_required
def edit_section(section_id):
    """Edit Konten Section di Sidebar Kiri Split Screen"""
    section = Section.query.get_or_404(section_id)
    page = section.page

    if request.method == "POST":
        content = dict(section.content or {})

        # 1. Update data dari teks form input
        for key, value in request.form.items():
            if key != "csrf_token":
                content[key] = value

        # 2. Update data dari file upload (Logo, Banner Hero, dll)
        for key, file in request.files.items():
            if file and file.filename != '':
                file_url = save_uploaded_file(file)
                if file_url:
                    # Menghilangkan suffix _file untuk mencocokkan key JSON (misal logo_url_file -> logo_url)
                    field_key = key.replace('_file', '')
                    content[field_key] = file_url

        section.content = content
        flag_modified(section, "content")
        section.updated_at = datetime.utcnow()
        page.updated_at = datetime.utcnow()
        db.session.commit()

        flash("Perubahan section berhasil disimpan!", "success")
        return redirect(url_for("admin.edit_section", section_id=section.id))

    # Jika diakses via GET, tampilkan layout split screen dengan tab edit terbuka
    return render_template("admin/manage_sections.html", section=section, page=page)

@admin_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    """Menghapus Section"""
    section = Section.query.get_or_404(section_id)
    page_id = section.page_id
    db.session.delete(section)
    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success", "message": "Section berhasil dihapus"})

    flash("Section berhasil dihapus!", "success")
    return redirect(url_for("admin.manage_section", page_id=page_id))

@admin_bp.route("/page/<int:page_id>/reorder", methods=["POST"])
@login_required
def reorder_sections(page_id):
    """AJAX Endpoint untuk menyimpan urutan Drag & Drop dari Sidebar"""
    page = Page.query.get_or_404(page_id)
    order_data = request.json.get("order", [])

    for item in order_data:
        section = Section.query.filter_by(id=item["id"], page_id=page.id).first()
        if section:
            section.order = item["order"]

    db.session.commit()
    return jsonify({"status": "ok", "message": "Urutan berhasil disimpan"})
# app/admin/sections.py
import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required
from sqlalchemy.orm.attributes import flag_modified
from app.admin import admin_bp
from app.admin.templates import (
    DEFAULT_SECTION_CONTENTS,
    SECTION_NAV_NAMES,
    generate_nav_items_for_page,
    save_uploaded_file
)
from app.models import Page, Section
from app.extensions import db


@admin_bp.route("/page/<int:page_id>/sections-manual")
@admin_bp.route("/page/<int:page_id>/manage")
@login_required
def manage_section(page_id):
    """Menampilkan Tampilan Builder Split Screen"""
    page = Page.query.get_or_404(page_id)
    return render_template("admin/manage_sections.html", page=page, section=None)


@admin_bp.route("/page/<int:page_id>/add-section", methods=["POST"])
@login_required
def add_section(page_id):
    """
    SINKRONISASI ARAH 1: TAMBAH SECTION -> OTOMATIS TAMBAH MENU DI NAVBAR
    """
    page = Page.query.get_or_404(page_id)
    section_type = request.form.get("type")

    if not section_type:
        flash("Jenis section wajib dipilih!", "danger")
        return redirect(url_for("admin.manage_section", page_id=page.id))

    last_order = db.session.query(db.func.max(Section.order)).filter_by(page_id=page.id).scalar() or 0
    sec_id_key = f"sec_{uuid.uuid4().hex[:8]}"

    initial_content = DEFAULT_SECTION_CONTENTS.get(section_type, {}).copy()

    # Ambil label default menu jika tersedia, jika tidak gunakan title-case biasa
    nav_text_default = SECTION_NAV_NAMES.get(section_type, section_type.replace('_', ' ').title())
    initial_content.setdefault("title", nav_text_default)
    initial_content["nav_id"] = sec_id_key

    # 1. KONDISI KHUSUS: Jika menambahkan NAVBAR baru
    if section_type == 'navbar':
        # Baca ulang semua section yang sudah ada di database untuk mengisi nav_items secara reaktif
        initial_content['nav_items'] = generate_nav_items_for_page(page.id)

    # 2. Buat Section Baru di DB
    new_section = Section(
        page_id=page.id,
        type=section_type,
        order=last_order + 1,
        content=initial_content
    )
    db.session.add(new_section)

    # 3. Otomatis Tambah Menu ke Navbar yang ADA (Jika section baru BUKAN Navbar atau Footer)
    if section_type not in ['navbar', 'footer']:
        navbar = Section.query.filter_by(page_id=page.id, type='navbar').first()
        if navbar:
            nav_content = dict(navbar.content or {})
            nav_items = nav_content.get('nav_items', [])

            nav_items.append({
                'id': sec_id_key,
                'text': initial_content.get("title", nav_text_default),
                'url': f"#{sec_id_key}",
                'type': section_type
            })
            nav_content['nav_items'] = nav_items
            navbar.content = nav_content
            flag_modified(navbar, "content")

    db.session.commit()
    flash(f"Section '{section_type}' berhasil ditambahkan!", "success")
    return redirect(url_for("admin.manage_section", page_id=page.id))


@admin_bp.route("/section/<int:section_id>/edit", methods=["GET", "POST"])
@login_required
def edit_section(section_id):
    """
    SINKRONISASI DUA ARAH: EDIT NAVBAR ATAU EDIT KONTEN SECTION
    """
    section = Section.query.get_or_404(section_id)
    page = section.page

    if request.method == "POST":
        content = dict(section.content or {})

        # ---------------------------------------------------------------------
        # A. KHUSUS NAVBAR (Arah Navbar -> Sections)
        # ---------------------------------------------------------------------
        if section.type == 'navbar':
            nav_texts = request.form.getlist("nav_texts[]")
            nav_types = request.form.getlist("nav_types[]")
            nav_ids = request.form.getlist("nav_ids[]")

            existing_sections = {
                s.content.get('nav_id'): s for s in page.sections
                if s.type not in ['navbar', 'footer'] and s.content and s.content.get('nav_id')
            }

            updated_nav_items = []
            kept_nav_ids = set()

            for i, text in enumerate(nav_texts):
                if not text.strip():
                    continue

                sec_type = nav_types[i] if i < len(nav_types) else 'about'
                sec_id_key = nav_ids[i] if (i < len(nav_ids) and nav_ids[i].strip()) else f"sec_{uuid.uuid4().hex[:8]}"

                kept_nav_ids.add(sec_id_key)

                # Update/Buat Section
                if sec_id_key in existing_sections:
                    sec_obj = existing_sections[sec_id_key]
                    sec_content = dict(sec_obj.content or {})
                    sec_content['title'] = text
                    sec_obj.content = sec_content
                    flag_modified(sec_obj, "content")
                else:
                    last_order = db.session.query(db.func.max(Section.order)).filter_by(page_id=page.id).scalar() or 0
                    init_content = DEFAULT_SECTION_CONTENTS.get(sec_type, {}).copy()
                    init_content['title'] = text
                    init_content['nav_id'] = sec_id_key

                    new_sec = Section(
                        page_id=page.id,
                        type=sec_type,
                        order=last_order + 1,
                        content=init_content
                    )
                    db.session.add(new_sec)

                updated_nav_items.append({
                    'id': sec_id_key,
                    'text': text,
                    'url': f"#{sec_id_key}",
                    'type': sec_type
                })

            # Hapus Section yang menunya dibuang dari Navbar
            for sec_key, sec_obj in existing_sections.items():
                if sec_key not in kept_nav_ids:
                    db.session.delete(sec_obj)

            content['nav_items'] = updated_nav_items
            content['brand_name'] = request.form.get('brand_name', '')
            content['button_text_1'] = request.form.get('button_text_1', '')
            content['button_link_1'] = request.form.get('button_link_1', '')

        # ---------------------------------------------------------------------
        # B. SECTION BIASA (Arah Section -> Navbar)
        # ---------------------------------------------------------------------
        else:
            for key, value in request.form.items():
                if key != "csrf_token" and not key.endswith("[]"):
                    content[key] = value

            # Jika Judul Section diubah, update teks di Navbar juga
            nav_id = content.get('nav_id')
            if nav_id and 'title' in content:
                navbar = Section.query.filter_by(page_id=page.id, type='navbar').first()
                if navbar:
                    nav_content = dict(navbar.content or {})
                    nav_items = nav_content.get('nav_items', [])
                    for item in nav_items:
                        if item.get('id') == nav_id or item.get('url') == f"#{nav_id}":
                            item['text'] = content['title']
                    nav_content['nav_items'] = nav_items
                    navbar.content = nav_content
                    flag_modified(navbar, "content")

        # Handling File Upload
        for key, file in request.files.items():
            if file and file.filename != '':
                file_url = save_uploaded_file(file)
                if file_url:
                    field_key = key.replace('_file', '')
                    content[field_key] = file_url

        section.content = content
        flag_modified(section, "content")
        section.updated_at = datetime.utcnow()
        page.updated_at = datetime.utcnow()
        db.session.commit()

        flash("Perubahan berhasil disimpan & disinkronkan!", "success")
        return redirect(url_for("admin.edit_section", section_id=section.id))

    return render_template("admin/manage_sections.html", section=section, page=page)


@admin_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    """
    SINKRONISASI HAPUS: HAPUS SECTION -> OTOMATIS HAPUS MENU DI NAVBAR
    """
    section = Section.query.get_or_404(section_id)
    page_id = section.page_id
    nav_id = section.content.get('nav_id') if section.content else None

    db.session.delete(section)

    # Hapus menu dari Navbar jika section memiliki nav_id
    if nav_id:
        navbar = Section.query.filter_by(page_id=page_id, type='navbar').first()
        if navbar:
            nav_content = dict(navbar.content or {})
            nav_items = nav_content.get('nav_items', [])
            nav_content['nav_items'] = [
                item for item in nav_items
                if item.get('id') != nav_id and item.get('url') != f"#{nav_id}"
            ]
            navbar.content = nav_content
            flag_modified(navbar, "content")

    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success", "message": "Section & Menu berhasil dihapus"})

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
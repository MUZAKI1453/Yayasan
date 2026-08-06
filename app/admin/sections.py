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
    """SINKRONISASI TAMBAH SECTION"""
    page = Page.query.get_or_404(page_id)
    section_type = request.form.get("type")

    if not section_type:
        flash("Jenis section wajib dipilih!", "danger")
        return redirect(url_for("admin.manage_section", page_id=page.id))

    last_order = db.session.query(db.func.max(Section.order)).filter_by(page_id=page.id).scalar() or 0
    sec_id_key = f"sec_{uuid.uuid4().hex[:8]}"

    initial_content = DEFAULT_SECTION_CONTENTS.get(section_type, {}).copy()
    nav_text_default = SECTION_NAV_NAMES.get(section_type, section_type.replace('_', ' ').title())
    initial_content.setdefault("title", nav_text_default)
    initial_content["nav_id"] = sec_id_key

    # Jika section tipe navbar
    if section_type == 'navbar':
        initial_content['nav_items'] = generate_nav_items_for_page(page.id)

    new_section = Section(
        page_id=page.id,
        type=section_type,
        order=last_order + 1,
        content=initial_content
    )
    db.session.add(new_section)

    # Otomatis tambah menu ke Navbar yang ada jika BUKAN navbar/footer
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
    EDIT KONTEN SECTION (NAVBAR, GALLERY, FOOTER, BIASA)
    """
    section = Section.query.get_or_404(section_id)
    page = section.page

    if request.method == "POST":
        content = dict(section.content or {})

        # ---------------------------------------------------------------------
        # A. KHUSUS NAVBAR
        # ---------------------------------------------------------------------
        if section.type == 'navbar':
            content['brand_name'] = request.form.get('brand_name', content.get('brand_name', ''))
            content['button_text_1'] = request.form.get('button_text_1', content.get('button_text_1', ''))
            content['button_link_1'] = request.form.get('button_link_1', content.get('button_link_1', ''))

            # SIMPAN TEMA, FONT, & WARNA DINAMIS NAVBAR
            content['nav_font_family'] = request.form.get('nav_font_family', 'Plus Jakarta Sans')
            content['nav_bg_color'] = request.form.get('nav_bg_color', '#ffffff')
            content['nav_text_color'] = request.form.get('nav_text_color', 'dark')
            content['button_bg_color'] = request.form.get('button_bg_color', '#2563eb')
            content['button_text_color'] = request.form.get('button_text_color', '#ffffff')

            nav_texts = request.form.getlist("nav_texts[]")
            nav_urls = request.form.getlist("nav_urls[]")
            nav_ids = request.form.getlist("nav_ids[]")

            if any(text.strip() for text in nav_texts):
                updated_nav_items = []
                for i, text in enumerate(nav_texts):
                    if text.strip():
                        sec_url = nav_urls[i] if i < len(nav_urls) else '#'
                        sec_id = nav_ids[i] if (i < len(nav_ids) and nav_ids[i].strip()) else sec_url.replace('#', '')

                        updated_nav_items.append({
                            'id': sec_id,
                            'text': text.strip(),
                            'url': sec_url if sec_url.startswith('#') else f"#{sec_url}"
                        })
                content['nav_items'] = updated_nav_items

        # ---------------------------------------------------------------------
        # B. KHUSUS GALLERY / DOKUMENTASI (MULTIPLE UPLOAD)
        # ---------------------------------------------------------------------
        elif section.type == 'gallery':
            content['title'] = request.form.get('title', 'Galeri & Dokumentasi')
            content['subtitle'] = request.form.get('subtitle', '')

            existing_urls = request.form.getlist('existing_photo_urls[]')
            captions = request.form.getlist('photo_captions[]')
            files = request.files.getlist('gallery_files[]')

            photos_list = []

            for i in range(len(existing_urls)):
                photo_url = existing_urls[i]
                caption = captions[i] if i < len(captions) else ''

                # Cek jika ada file gambar baru yang di-upload untuk baris ini
                if i < len(files) and files[i] and files[i].filename != '':
                    uploaded_url = save_uploaded_file(files[i])
                    if uploaded_url:
                        photo_url = uploaded_url

                if photo_url:
                    photos_list.append({
                        'url': photo_url,
                        'caption': caption
                    })

            content['photos'] = photos_list

        # ---------------------------------------------------------------------
        # C. SECTION BIASA (HERO, FOOTER, ABOUT, DLL)
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

        # Handling Upload File Tunggal Umum (Logo / Gambar latar / Photo tunggal)
        for key, file in request.files.items():
            if key != 'gallery_files[]' and file and file.filename != '':
                file_url = save_uploaded_file(file)
                if file_url:
                    field_key = key.replace('_file', '')
                    content[field_key] = file_url

        section.content = content
        flag_modified(section, "content")
        section.updated_at = datetime.utcnow()
        page.updated_at = datetime.utcnow()
        db.session.commit()

        flash("Perubahan berhasil disimpan!", "success")
        return redirect(url_for("admin.manage_section", page_id=page.id))

    return render_template("admin/manage_sections.html", section=section, page=page)


@admin_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    """HAPUS SECTION DAN MENU TERHUBUNG"""
    section = Section.query.get_or_404(section_id)
    page_id = section.page_id
    nav_id = section.content.get('nav_id') if section.content else None

    db.session.delete(section)

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
    """AJAX Drag & Drop Order"""
    page = Page.query.get_or_404(page_id)
    order_data = request.json.get("order", [])

    for item in order_data:
        section = Section.query.filter_by(id=item["id"], page_id=page.id).first()
        if section:
            section.order = item["order"]

    db.session.commit()
    return jsonify({"status": "ok", "message": "Urutan berhasil disimpan"})
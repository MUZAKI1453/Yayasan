import re
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

    if section_type == 'navbar':
        initial_content['nav_items'] = generate_nav_items_for_page(page.id)

    new_section = Section(
        page_id=page.id,
        type=section_type,
        order=last_order + 1,
        content=initial_content
    )
    db.session.add(new_section)

    db.session.commit()
    flash(f"Section '{section_type}' berhasil ditambahkan!", "success")
    return redirect(url_for("admin.manage_section", page_id=page.id))


@admin_bp.route("/section/<int:section_id>/edit", methods=["GET", "POST"])
@login_required
def edit_section(section_id):
    """
    EDIT KONTEN & TATA LETAK SECTION
    Mendukung pergeseran kursor, multi-image layer independen, alignment, font, background texture, dan file uploads.
    """
    section = Section.query.get_or_404(section_id)
    page = section.page

    if request.method == "POST":
        content = dict(section.content or {})

        # --- 1. PROSES FORM DENGAN PREFIX 'content.' ---
        for key, value in request.form.items():
            if key.startswith('content.'):
                content_key = key.replace('content.', '')
                content[content_key] = value.strip() if isinstance(value, str) else value

        # Fallback title
        if 'title' in request.form:
            content['title'] = request.form.get('title', '').strip()

        # --- 2. PENANGANAN SPESIFIK BERDASARKAN TIPE SECTION ---
        if section.type == 'navbar':
            content['brand_name'] = request.form.get('brand_name', content.get('brand_name', '')).strip()

            def parse_nav_items(prefix='nav_parents'):
                parents = {}
                pattern = re.compile(rf'^{re.escape(prefix)}\[(\d+)\]\[(.+?)\]$')
                for key, value in request.form.items():
                    m = pattern.match(key)
                    if not m:
                        continue
                    idx, field = int(m.group(1)), m.group(2)
                    parents.setdefault(idx, {})[field] = value.strip() if isinstance(value, str) else value

                items = []
                for idx in sorted(parents):
                    raw = parents[idx]
                    text = raw.get('text', '').strip()
                    target_id = raw.get('target_section_id', '').strip()
                    item = {
                        'id': raw.get('id') or f'nav_{uuid.uuid4().hex[:8]}',
                        'text': text,
                        'target_section_id': int(target_id) if target_id.isdigit() else None,
                        'target_type': (
                            Section.query.get(int(target_id)).type if target_id.isdigit() and Section.query.get(
                                int(target_id)) else None),
                        'children': []
                    }
                    child_texts = request.form.getlist(f'{prefix}[{idx}][children][][text]')
                    child_targets = request.form.getlist(f'{prefix}[{idx}][children][][target_section_id]')
                    for cidx, child_text in enumerate(child_texts):
                        child_text = child_text.strip()
                        if not child_text:
                            continue
                        child_target = child_targets[cidx].strip() if cidx < len(child_targets) else ''
                        item['children'].append({
                            'id': f'nav_{uuid.uuid4().hex[:8]}',
                            'text': child_text,
                            'target_section_id': int(child_target) if child_target.isdigit() else None,
                            'target_type': (Section.query.get(
                                int(child_target)).type if child_target.isdigit() and Section.query.get(
                                int(child_target)) else None)
                        })
                    if text:
                        items.append(item)
                return items

            content['nav_items'] = parse_nav_items()
            content['button_enabled'] = '1' in request.form.getlist('button_enabled')
            content['button_text_1'] = request.form.get('button_text_1', '').strip()
            target = request.form.get('button_target_section_id', '').strip()
            content['button_target_section_id'] = int(target) if target.isdigit() else None
            content['button_link_1'] = request.form.get('button_link_1', '').strip()
            content['button_bg_color'] = request.form.get('button_bg_color', content.get('button_bg_color', '#2563eb'))
            content['button_text_color'] = request.form.get('button_text_color',
                                                            content.get('button_text_color', '#ffffff'))

        elif section.type == 'hero':
            content['cta_enabled'] = request.form.get('cta_enabled', '0') == '1'

            # A. BACA LIST GAMBAR LAMA
            raw_images = request.form.getlist('content.images') or request.form.getlist('existing_images[]')
            if not raw_images:
                single_img = request.form.get('content.image_url') or content.get('image_url') or content.get('image')
                raw_images = [single_img] if single_img else []

            # PERBAIKAN BANYAK GAMBAR: PROSES HAPUS DAN GANTI GAMBAR TERDAPAT
            processed_images = []
            for idx, img_url in enumerate(raw_images):
                # Cek apakah checkbox hapus dicentang untuk indeks ini
                is_deleted = request.form.get(f'delete_image_{idx}') == '1'

                # Cek apakah ada file pengganti yang diupload untuk indeks ini
                replacement_file = request.files.get(f'hero_image_{idx}')

                if is_deleted:
                    continue  # Abaikan / hapus dari array
                elif replacement_file and replacement_file.filename != '':
                    new_url = save_uploaded_file(replacement_file)
                    if new_url:
                        processed_images.append(new_url)
                elif img_url and img_url.strip() != '':
                    processed_images.append(img_url.strip())

            # B. UPLOAD GAMBAR BARU (JIKA ADA DARI FIELD TAMBAH GAMBAR BARU)
            add_image_file = request.files.get('add_hero_image')
            if add_image_file and add_image_file.filename != '':
                new_add_url = save_uploaded_file(add_image_file)
                if new_add_url:
                    processed_images.append(new_add_url)

            # SINKRONISASI HASIL AKHIR PADA CONTENT
            content['images'] = processed_images
            if processed_images:
                content['image_url'] = processed_images[0]
                content['image'] = processed_images[0]
            else:
                content['image_url'] = ''
                content['image'] = ''

            # BACKGROUND IMAGE HANDLING
            existing_bg_image = request.form.get('content.bg_image_url') or content.get('bg_image_url')
            if existing_bg_image:
                content['bg_image_url'] = existing_bg_image

            bg_image_preset = request.form.get('content.bg_image_preset')
            if bg_image_preset:
                content['bg_image_url'] = bg_image_preset

            bg_file = request.files.get('bg_image') or request.files.get('content.bg_image')
            if bg_file and bg_file.filename != '':
                uploaded_bg_url = save_uploaded_file(bg_file)
                if uploaded_bg_url:
                    content['bg_image_url'] = uploaded_bg_url

        elif section.type == 'gallery':
            pass

        # --- 4. UNIVERSAL FILE UPLOADER ---
        excluded_file_keys = [
            'gallery_files[]', 'image_file', 'logo_file', 'logo',
            'qris_file', 'image', 'content.image', 'bg_image', 'hero_image',
            'hero_images', 'images', 'hero_images[]', 'content.images', 'content.image_url',
            'add_hero_image'
        ]
        # Filter juga kunci file hero_image_{idx} agar tidak menimpa otomatis
        for key, file in request.files.items():
            if key not in excluded_file_keys and not key.startswith('hero_image_') and not key.startswith(
                    'slides[') and file and file.filename != '':
                file_url = save_uploaded_file(file)
                if file_url:
                    field_key = key.replace('_file', '').replace('content.', '')
                    content[field_key] = file_url

        # --- 5. SIMPAN KE DATABASE ---
        section.content = content
        flag_modified(section, "content")
        section.updated_at = datetime.utcnow()
        if page:
            page.updated_at = datetime.utcnow()

        db.session.commit()

        flash("Perubahan berhasil disimpan!", "success")
        return redirect(url_for("admin.manage_section", page_id=page.id, section_id=section.id))

    return render_template("admin/manage_sections.html", section=section, page=page)


@admin_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    """HAPUS SECTION DAN MENU TERHUBUNG"""
    section = Section.query.get_or_404(section_id)
    page_id = section.page_id
    db.session.delete(section)
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
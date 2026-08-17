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

        # --- 1. PROSES FORM DENGAN PREFIX 'content.' (TERMASUK KOORDINAT INDIVIDUAL POS_IMG_0_X, POS_IMG_1_X, DLL.) ---
        for key, value in request.form.items():
            if key.startswith('content.'):
                content_key = key.replace('content.', '')
                content[content_key] = value.strip() if isinstance(value, str) else value

        # --- 2. PENANGANAN SPESIFIK BERDASARKAN TIPE SECTION ---
        if section.type == 'navbar':
            content['brand_name'] = request.form.get('brand_name', content.get('brand_name', '')).strip()

            # Navbar dikelola sepenuhnya manual. Target menu disimpan sebagai ID Section,
            # bukan URL #sec_xxx yang harus diketahui admin.
            def parse_nav_items(prefix='nav_parents'):
                import re as _re
                parents = {}
                pattern = _re.compile(rf'^{_re.escape(prefix)}\[(\d+)\]\[(.+?)\]$')
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
                        'target_type': (Section.query.get(int(target_id)).type if target_id.isdigit() and Section.query.get(int(target_id)) else None),
                        'children': []
                    }
                    # Parent boleh menjadi dropdown tanpa target.
                    child_pattern = _re.compile(r'^children\[\]\[(text|target_section_id)\]$')
                    # Browser mengirim pasangan [] secara berurutan; ambil langsung dari form list.
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
                            'target_type': (Section.query.get(int(child_target)).type if child_target.isdigit() and Section.query.get(int(child_target)) else None)
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
            content['button_text_color'] = request.form.get('button_text_color', content.get('button_text_color', '#ffffff'))

        elif section.type == 'hero':
            content['cta_enabled'] = request.form.get('cta_enabled', '0') == '1'
            # A. PERTAHANKAN LIST GAMBAR YANG SUDAH ADA DARI FORM ATAU DATABASE
            existing_images = request.form.getlist('content.existing_images') or request.form.getlist('existing_images[]')
            existing_single_img = request.form.get('content.image_url') or request.form.get('content.existing_image') or content.get('image_url') or content.get('image')

            if existing_images:
                content['images'] = existing_images
            elif existing_single_img and 'images' not in content:
                content['images'] = [existing_single_img]

            if existing_single_img:
                content['image_url'] = existing_single_img
                content['image'] = existing_single_img

            existing_bg_image = request.form.get('content.bg_image_url') or request.form.get('content.existing_bg_image') or content.get('bg_image_url')
            if existing_bg_image:
                content['bg_image_url'] = existing_bg_image

            # B. PRESET TEKSTUR BACKGROUND
            bg_image_preset = request.form.get('content.bg_image_preset')
            if bg_image_preset:
                content['bg_image_url'] = bg_image_preset

            # C. UPLOAD MULTIPLE GAMBAR HERO INDEPENDEN
            hero_files = (
                request.files.getlist('hero_images') or
                request.files.getlist('images') or
                request.files.getlist('hero_images[]') or
                request.files.getlist('content.images')
            )

            # Fallback jika hanya 1 file diunggah via input file biasa
            if not hero_files or all(f.filename == '' for f in hero_files):
                single_file = (
                    request.files.get('hero_image') or
                    request.files.get('image') or
                    request.files.get('content.image') or
                    request.files.get('content.image_url')
                )
                if single_file and single_file.filename != '':
                    hero_files = [single_file]

            # Simpan file gambar baru yang diunggah
            uploaded_urls = []
            for file in hero_files:
                if file and file.filename != '':
                    file_url = save_uploaded_file(file)
                    if file_url:
                        uploaded_urls.append(file_url)

            # Jika ada gambar baru, tambahkan ke list 'images'
            if uploaded_urls:
                current_images = content.get('images', [])
                if not isinstance(current_images, list):
                    current_images = [current_images] if current_images else []

                updated_images = current_images + uploaded_urls
                content['images'] = updated_images

                # Sinkronisasi gambar pertama untuk kompatibilitas template lama
                content['image_url'] = updated_images[0]
                content['image'] = updated_images[0]

            # Sinkronisasi koordinat gambar index 0 ke pos_img_x/y/w utama
            if 'images' in content and isinstance(content['images'], list) and len(content['images']) > 0:
                if 'pos_img_0_x' not in content and 'pos_img_x' in content:
                    content['pos_img_0_x'] = content['pos_img_x']
                if 'pos_img_0_y' not in content and 'pos_img_y' in content:
                    content['pos_img_0_y'] = content['pos_img_y']
                if 'pos_img_0_w' not in content and 'pos_img_w' in content:
                    content['pos_img_0_w'] = content['pos_img_w']

            # D. UPLOAD GAMBAR BACKGROUND HERO
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
            'hero_images', 'images', 'hero_images[]', 'content.images', 'content.image_url'
        ]
        for key, file in request.files.items():
            if key not in excluded_file_keys and not key.startswith('slides[') and file and file.filename != '':
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

        flash("Perubahan tata letak dan konten berhasil disimpan!", "success")
        return redirect(url_for("admin.manage_section", page_id=page.id, section_id=section.id))

    return render_template("admin/manage_sections.html", section=section, page=page)


@admin_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    """HAPUS SECTION DAN MENU TERHUBUNG"""
    section = Section.query.get_or_404(section_id)
    page_id = section.page_id
    # Section dan Navbar sengaja independent. Menghapus Section tidak menghapus
    # menu Navbar; menu yang targetnya sudah tidak ada akan dirender sebagai link kosong.
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
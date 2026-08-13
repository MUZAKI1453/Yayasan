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

    if section_type not in ['navbar', 'footer']:
        navbar = Section.query.filter_by(page_id=page.id, type='navbar').first()
        if navbar:
            nav_content = dict(navbar.content or {})
            nav_items = nav_content.get('nav_items', [])

            nav_items.append({
                'id': sec_id_key,
                'text': initial_content.get("title", nav_text_default),
                'url': f"#{sec_id_key}",
                'children': [],
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
    EDIT KONTEN SECTION
    """
    section = Section.query.get_or_404(section_id)
    page = section.page

    if request.method == "POST":
        content = dict(section.content or {})

        if section.type == 'navbar':
            content['brand_name'] = request.form.get('brand_name', content.get('brand_name', '')).strip()
            content['brand_subtitle'] = request.form.get('brand_subtitle',
                                                         content.get('brand_subtitle', 'Official Portal')).strip()
            content['button_text_1'] = request.form.get('button_text_1', content.get('button_text_1', '')).strip()
            content['button_link_1'] = request.form.get('button_link_1', content.get('button_link_1', '')).strip()

            content['nav_font_family'] = request.form.get('nav_font_family', 'Plus Jakarta Sans')
            content['nav_bg_color'] = request.form.get('nav_bg_color', '#ffffff')
            content['nav_text_color'] = request.form.get('nav_text_color', 'dark')
            content['button_bg_color'] = request.form.get('button_bg_color', '#2563eb')
            content['button_text_color'] = request.form.get('button_text_color', '#ffffff')

            updated_nav_items = []

            parent_indices = sorted(list(set(
                re.findall(r'nav_parents\[(\d+)\]', key)[0]
                for key in request.form.keys()
                if key.startswith('nav_parents[')
            )), key=int)

            if parent_indices:
                for idx in parent_indices:
                    p_text = request.form.get(f'nav_parents[{idx}][text]', '').strip()
                    p_url = request.form.get(f'nav_parents[{idx}][url]', '').strip()

                    p_text = SECTION_NAV_NAMES.get(p_text, p_text)

                    if p_text:
                        if p_url and not (p_url.startswith('#') or p_url.startswith('http://') or p_url.startswith(
                                'https://') or p_url.startswith('/')):
                            p_url = f"#{p_url}"
                        elif not p_url:
                            p_url = "#"

                        children = []
                        child_texts = request.form.getlist(f'nav_parents[{idx}][children][][text]')
                        child_urls = request.form.getlist(f'nav_parents[{idx}][children][][url]')

                        if not child_texts:
                            child_keys = sorted(list(set(
                                re.findall(rf'nav_parents\[{idx}\]\[children\]\[(\d+)\]', k)[0]
                                for k in request.form.keys()
                                if k.startswith(f'nav_parents[{idx}][children][')
                            )), key=int)
                            for c_idx in child_keys:
                                c_t = request.form.get(f'nav_parents[{idx}][children][{c_idx}][text]', '').strip()
                                c_u = request.form.get(f'nav_parents[{idx}][children][{c_idx}][url]', '').strip()
                                if c_t:
                                    child_texts.append(c_t)
                                    child_urls.append(c_u)

                        for c_text, c_url in zip(child_texts, child_urls):
                            c_text = c_text.strip()
                            c_url = c_url.strip()
                            if c_text:
                                pretty_c_text = SECTION_NAV_NAMES.get(c_text, c_text.replace('_', ' ').title())

                                if c_url and not (
                                        c_url.startswith('#') or c_url.startswith('http://') or c_url.startswith(
                                        'https://') or c_url.startswith('/')):
                                    c_url = f"#{c_url}"
                                elif not c_url:
                                    c_url = "#"
                                children.append({
                                    'text': pretty_c_text,
                                    'url': c_url
                                })

                        parent_item = {
                            'id': f"sec_{p_url.replace('#', '')}",
                            'text': p_text,
                            'url': p_url,
                            'children': children
                        }
                        updated_nav_items.append(parent_item)

                content['nav_items'] = updated_nav_items
            else:
                nav_texts = request.form.getlist("nav_texts[]")
                nav_urls = request.form.getlist("nav_urls[]")
                nav_ids = request.form.getlist("nav_ids[]")

                if any(text.strip() for text in nav_texts):
                    for i, text in enumerate(nav_texts):
                        t_clean = text.strip()
                        if t_clean:
                            sec_url = nav_urls[i] if i < len(nav_urls) else '#'
                            sec_id = nav_ids[i] if (i < len(nav_ids) and nav_ids[i].strip()) else sec_url.replace('#',
                                                                                                                  '')

                            updated_nav_items.append({
                                'id': sec_id,
                                'text': SECTION_NAV_NAMES.get(t_clean, t_clean),
                                'url': sec_url if (
                                            sec_url.startswith('#') or sec_url.startswith('http')) else f"#{sec_url}",
                                'children': []
                            })
                    content['nav_items'] = updated_nav_items

        elif section.type == 'hero':
            slide_indices = sorted({
                int(match.group(1))
                for key in request.form.keys()
                for match in [re.match(r'slides\[(\d+)\]\[', key)]
                if match
            })

            slides = []
            for idx in slide_indices:
                image_url = request.form.get(f'slides[{idx}][existing_image]', '').strip()
                uploaded_file = request.files.get(f'slides[{idx}][image]')

                if uploaded_file and uploaded_file.filename:
                    uploaded_url = save_uploaded_file(uploaded_file)
                    if uploaded_url:
                        image_url = uploaded_url

                eyebrow = request.form.get(f'slides[{idx}][eyebrow]', '').strip()
                title = request.form.get(f'slides[{idx}][title]', '').strip()
                subtitle = request.form.get(f'slides[{idx}][subtitle]', '').strip()
                cta_text = request.form.get(f'slides[{idx}][cta_text]', '').strip()
                cta_url = request.form.get(f'slides[{idx}][cta_url]', '#').strip() or '#'

                if not any([image_url, eyebrow, title, subtitle, cta_text]):
                    continue

                slides.append({
                    'image': image_url,
                    'eyebrow': eyebrow,
                    'title': title,
                    'subtitle': subtitle,
                    'cta': {
                        'text': cta_text,
                        'url': cta_url
                    }
                })

            content = {'slides': slides}

        elif section.type == 'gallery':
            content['title'] = request.form.get('title', 'Galeri & Dokumentasi').strip()
            content['subtitle'] = request.form.get('subtitle', '').strip()

            existing_urls = request.form.getlist('existing_photo_urls[]')
            captions = request.form.getlist('photo_captions[]')
            files = request.files.getlist('gallery_files[]')

            photos_list = []

            for i in range(len(existing_urls)):
                photo_url = existing_urls[i]
                caption = captions[i] if i < len(captions) else ''

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

        elif section.type == 'about':
            content['title'] = request.form.get('title', '').strip()
            content['eyebrow'] = request.form.get('eyebrow', '').strip()
            content['description'] = request.form.get('description', request.form.get('content', '')).strip()
            content['image_caption'] = request.form.get('image_caption', '').strip()

            old_image = request.form.get('image', '').strip() or content.get('image_url', '') or content.get('image',
                                                                                                             '')
            uploaded_file = request.files.get('image_file')
            if uploaded_file and uploaded_file.filename:
                saved_url = save_uploaded_file(uploaded_file)
                if saved_url:
                    old_image = saved_url
            content['image_url'] = old_image

            content['button'] = {
                'text': request.form.get('button_text_1', '').strip(),
                'url': request.form.get('button_link_1', '').strip() or '#'
            }

        # --- TERKINI: HANDLER UNTUK SECTION VISION_MISSION ---
        elif section.type == 'vision_mission':
            content['eyebrow'] = request.form.get('eyebrow', 'Arah & Tujuan').strip()
            content['title'] = request.form.get('title', 'Visi & Misi').strip()
            content['subtitle'] = request.form.get('subtitle', '').strip()
            content['visi'] = request.form.get('visi', '').strip()

            # Menangkap array poin-poin misi dari input dinamis misi[]
            misi_items = request.form.getlist('misi[]')
            content['misi'] = [m.strip() for m in misi_items if m.strip()]

        elif section.type == 'features':
            content['title'] = request.form.get('title', 'Keunggulan & Fasilitas Kami').strip()
            content['subtitle'] = request.form.get('subtitle', '').strip()

            item_indices = sorted(list(set(
                re.findall(r'items\[(\d+)\]', key)[0]
                for key in request.form.keys()
                if key.startswith('items[')
            )), key=int)

            features_list = []
            for idx in item_indices:
                f_title = request.form.get(f'items[{idx}][title]', '').strip()
                f_desc = request.form.get(f'items[{idx}][description]',
                                          request.form.get(f'items[{idx}][desc]', '')).strip()
                f_icon = request.form.get(f'items[{idx}][icon]', 'bi-check-circle').strip()

                if f_title:
                    features_list.append({
                        'title': f_title,
                        'desc': f_desc,
                        'description': f_desc,
                        'icon': f_icon or 'bi-check-circle'
                    })

            content['items'] = features_list

        elif section.type == 'testimonial':
            content['title'] = request.form.get('title', content.get('title', 'Testimoni')).strip()
            content['subtitle'] = request.form.get('subtitle', content.get('subtitle', '')).strip()

            item_indices = sorted({
                int(match.group(1))
                for key in request.form.keys()
                for match in [re.match(r'items\[(\d+)\]\[(?:name|quote)\]$', key)]
                if match
            })

            items = []
            for idx in item_indices:
                name = request.form.get(f'items[{idx}][name]', '').strip()
                quote = request.form.get(f'items[{idx}][quote]', '').strip()
                if name or quote:
                    items.append({
                        'name': name,
                        'quote': quote
                    })

            content['items'] = items

        elif section.type == 'faq':
            content['title'] = request.form.get('title', content.get('title', 'Pertanyaan Umum (FAQ)')).strip()
            content['subtitle'] = request.form.get('subtitle', content.get('subtitle', '')).strip()

            item_indices = sorted({
                int(match.group(1))
                for key in request.form.keys()
                for match in [re.match(r'items\[(\d+)\]\[(?:question|answer)\]$', key)]
                if match
            })

            items = []
            for idx in item_indices:
                question = request.form.get(f'items[{idx}][question]', '').strip()
                answer = request.form.get(f'items[{idx}][answer]', '').strip()
                if question or answer:
                    items.append({
                        'question': question,
                        'answer': answer
                    })

            content['items'] = items

        elif section.type == 'cta':
            content = {
                'nav_id': content.get('nav_id'),
                'title': request.form.get('title', '').strip(),
                'subtitle': request.form.get('subtitle', '').strip(),
                'button': {
                    'text': request.form.get('button_text', '').strip(),
                    'url': request.form.get('button_url', '#').strip() or '#'
                }
            }

        elif section.type == 'progress':
            content['title'] = request.form.get('title', 'Progress Kuota Pendaftaran').strip()
            content['subtitle'] = request.form.get('subtitle', '').strip()

            try:
                content['target_quota'] = float(request.form.get('target_quota', 0) or 0)
            except (TypeError, ValueError):
                content['target_quota'] = 0

            try:
                content['filled_quota'] = float(request.form.get('filled_quota', 0) or 0)
            except (TypeError, ValueError):
                content['filled_quota'] = 0

            button_text = request.form.get('button_text', request.form.get('button_text_1', '')).strip()
            button_url = request.form.get('button_url', request.form.get('button_link_1', '#')).strip() or '#'
            content['button'] = {
                'text': button_text,
                'url': button_url
            }

        elif section.type == 'footer':
            content['title'] = request.form.get('title', '').strip()
            content['description'] = request.form.get('description', '').strip()
            content['address'] = request.form.get('address', '').strip()
            content['phone'] = request.form.get('phone', '').strip()
            content['whatsapp_number'] = request.form.get('whatsapp', request.form.get('whatsapp_number', '')).strip()
            content['email'] = request.form.get('email', '').strip()

            # --- SOSIAL MEDIA ---
            content['facebook_url'] = request.form.get('facebook_url', '').strip()
            content['instagram_url'] = request.form.get('instagram_url', '').strip()
            content['youtube_url'] = request.form.get('youtube_url', '').strip()
            content['tiktok_url'] = request.form.get('tiktok_url', '').strip()

            # --- PETA & LOKASI ---
            content['maps_url'] = request.form.get('maps_url', request.form.get('google_maps_link', '')).strip()
            content['maps_embed_url'] = request.form.get('maps_embed_url', request.form.get('maps_embed', '')).strip()

            content['copyright'] = request.form.get('copyright', '').strip()

            # --- UPLOAD LOGO FOOTER ---
            logo_file = request.files.get('logo_file') or request.files.get('logo')
            if logo_file and logo_file.filename != '':
                saved_logo = save_uploaded_file(logo_file)
                if saved_logo:
                    content['logo_url'] = saved_logo
            else:
                existing_logo = request.form.get('existing_logo', request.form.get('logo_url', '')).strip()
                if existing_logo:
                    content['logo_url'] = existing_logo

        elif section.type == 'donation_campaign':
            content['eyebrow'] = request.form.get('eyebrow', 'PROGRAM KEBAIKAN').strip()
            content['title'] = request.form.get('title', 'Program Donasi & Wakaf').strip()
            content['subtitle'] = request.form.get('subtitle', '').strip()

            # Target & Capaian Nominal
            try:
                content['target'] = float(request.form.get('target', 0) or 0)
            except (TypeError, ValueError):
                content['target'] = 0

            try:
                content['collected'] = float(request.form.get('collected', 0) or 0)
            except (TypeError, ValueError):
                content['collected'] = 0

            # --- MULTI REKENING BANK ---
            bank_accounts = request.form.getlist('bank_accounts[]')
            clean_banks = [b.strip() for b in bank_accounts if b.strip()]

            single_bank = request.form.get('bank_account', '').strip()
            if single_bank and single_bank not in clean_banks:
                clean_banks.insert(0, single_bank)

            content['bank_accounts'] = clean_banks
            content['bank_account'] = clean_banks[0] if clean_banks else ''

            # --- INFORMASI KONFIRMASI & TELEPON ADMIN ---
            confirm_info = request.form.get('confirm_info', 'Konfirmasi transfer via Admin Keuangan:').strip()
            admin_phone = request.form.get('admin_phone', '').strip()
            button_text = request.form.get('button_text', 'Klik disini untuk konfirmasi').strip()

            content['confirm_info'] = confirm_info
            content['admin_phone'] = admin_phone
            content['button_text'] = button_text

            # --- GENERATE LINK WHATSAPP ---
            clean_phone = ''.join(filter(str.isdigit, admin_phone))
            if clean_phone.startswith('0'):
                clean_phone = '62' + clean_phone[1:]
            elif clean_phone.startswith('8'):
                clean_phone = '62' + clean_phone

            if clean_phone:
                content['button_link'] = f"https://wa.me/{clean_phone}"
            else:
                content['button_link'] = request.form.get('button_link', '#').strip()

            # --- UPLOAD GAMBAR BARCODE QRIS ---
            qris_file = request.files.get('qris_file')
            if qris_file and qris_file.filename != '':
                saved_qris = save_uploaded_file(qris_file)
                if saved_qris:
                    content['qris_image'] = saved_qris
            else:
                content['qris_image'] = request.form.get('existing_qris', content.get('qris_image', '')).strip()

        else:
            for key, value in request.form.items():
                if key != "csrf_token" and not key.endswith("[]"):
                    content[key] = value

        # SINKRONISASI UPDATE JUDUL SECTION KE NAVBAR LINK AUTOMATIS
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

        # --- UNIVERSAL FILE UPLOADER ---
        excluded_file_keys = ['gallery_files[]', 'hero_bg_files[]', 'image_file', 'logo_file', 'logo', 'qris_file']

        for key, file in request.files.items():
            if key not in excluded_file_keys and not key.startswith('slide_bg_files_') and file and file.filename != '':
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
        return redirect(url_for("admin.manage_section", page_id=page.id, section_id=section.id))

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
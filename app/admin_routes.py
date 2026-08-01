import re, os, uuid
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.utils import secure_filename
from flask import current_app

from app.models import User, Page, Section
from app.extensions import db

admin_bp = Blueprint("admin", __name__)


# ==============================================================================
# DICTIONARY KONTEN DEFAULT UNTUK SETIAP SECTION
# ==============================================================================
DEFAULT_SECTION_CONTENTS = {
    "navbar": {
        "brand_name": "SDIP Baitussalam",
        "logo_url": "",
        "nav_text_1": "Beranda", "nav_url_1": "#beranda",
        "nav_text_2": "Tentang", "nav_url_2": "#tentang",
        "nav_text_3": "Program", "nav_url_3": "#program",
        "nav_text_4": "Kontak", "nav_url_4": "#kontak",
        "button_text": "Donasi Sekarang",
        "button_link": "#donasi"
    },
    "hero": {
        "eyebrow": "Campaign Baru 2026",
        "title": "Judul Utama Campaign",
        "subtitle": "Tuliskan ringkasan atau kutipan singkat diawal halaman...",
        "button_text": "Donasi Sekarang",
        "button_link": "#donasi",
        "background_image": ""
    },
    "progress": {
        "title": "Progress Donasi",
        "target": 100000000,
        "collected": 0,
        "extra_text": "Mari bersama-sama membantu sesama"
    },
    "about": {
        "eyebrow": "Tentang Campaign",
        "title": "Cerita Campaign",
        "content": "Tuliskan latar belakang dan cerita lengkap mengenai campaign ini...",
        "image": "",
        "image_caption": ""
    },
    "features": {
        "title": "Keunggulan",
        "subtitle": "Mengapa harus berdonasi di sini?",
        "item1_title": "Transparan", "item1_desc": "Laporan keuangan diperbarui secara berkala.",
        "item2_title": "Amanah", "item2_desc": "Penyaluran langsung ke penerima manfaat.",
        "item3_title": "Cepat", "item3_desc": "Proses donasi yang praktis dan mudah.",
        "item4_title": "Bermanfaat", "item4_desc": "Dampak jangka panjang bagi sesama."
    },
    "gallery": {
        "title": "Galeri Dokumentasi",
        "subtitle": "Foto-foto kegiatan dan penyaluran donasi",
        "image1": "", "image2": "", "image3": "", "image4": "", "image5": "", "image6": ""
    },
    "testimonial": {
        "title": "Apa Kata Mereka",
        "name1": "Hamba Allah", "role1": "Donatur", "quote1": "Semoga amanah dan bermanfaat.",
        "name2": "Ibu Dermawan", "role2": "Donatur", "quote2": "Senang bisa membantu sesama.",
        "name3": "Anak Sholeh", "role3": "Donatur", "quote3": "Terima kasih atas kerja kerasnya."
    },
    "faq": {
        "title": "Pertanyaan Umum (FAQ)",
        "faq_q1": "Bagaimana cara berdonasi?", "faq_a1": "Klik tombol Donasi Sekarang lalu ikuti petunjuk instruksi pembayaran.",
        "faq_q2": "Apakah donasi saya tercatat?", "faq_a2": "Ya, setiap transaksi akan langsung masuk dalam riwayat donasi.",
        "faq_q3": "Apakah ada batasan nominal?", "faq_a3": "Tidak ada, Anda bisa berdonasi dengan nominal berapa pun.",
        "faq_q4": "Siapa yang mengelola dana ini?", "faq_a4": "Tim yayasan bekerja sama dengan relawan lapangan terverifikasi."
    },
    "cta": {
        "title": "Mari Bersama Membantu",
        "subtitle": "Ulurkan tangan Anda untuk kebaikan dan kemanusiaan",
        "button_text": "Donasi Sekarang",
        "button_link": "#donasi"
    },
    "footer": {
        "copyright": "© 2026 Yayasan Kita. All rights reserved.",
        "description": "Lembaga nirlaba yang berfokus pada pendidikan dan kemanusiaan.",
        "facebook": "#",
        "instagram": "#",
        "whatsapp": "#"
    },
    "updates": {
        "title": "Kabar Terbaru / Perkemabangan",
        "content": "Penyaluran bantuan tahap 1 telah berhasil dilaksanakan..."
    },
    "budget_breakdown": {
        "title": "Rincian Alokasi Dana",
        "content": "70% Bantuan Langsung, 20% Operasional Lapangan, 10% Pengembangan."
    },
    "donor_list": {
        "title": "Donatur Terbaru",
        "content": "Terima kasih kepada para donatur yang telah menyalurkan bantuannya."
    },
    "team": {
        "title": "Tim Pengelola Campaign",
        "content": "Tim kami terdiri dari para relawan terverifikasi."
    },
    "location": {
        "title": "Lokasi Penyaluran",
        "content": "Penyaluran bantuan dipusatkan di lokasi target penerima."
    }
}


# ==============================================================================
# 1. AUTHENTICATION (Login / Logout)
# ==============================================================================

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username dan password wajib diisi!", "warning")
            return render_template("admin/login.html")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        else:
            flash("Username atau password salah!", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


# ==============================================================================
# 2. DASHBOARD
# ==============================================================================

@admin_bp.route("/")
@login_required
def dashboard():
    pages = Page.query.order_by(Page.updated_at.desc()).all()
    return render_template("admin/dashboard.html", pages=pages)


# ==============================================================================
# 3. PAGES (CAMPAIGN) MANAGEMENT
# ==============================================================================

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
        creation_mode = request.form.get("creation_mode", "template")

        if not title:
            flash("Judul wajib diisi", "danger")
            return redirect(url_for("admin.new_page"))

        # Generate slug otomatis
        slug = re.sub(r"[^a-z0-9-]", "-", title.lower()).strip("-")
        base_slug = slug
        counter = 1

        while Page.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        page = Page(title=title, slug=slug, is_published=True)
        db.session.add(page)
        db.session.flush()

        if creation_mode == "template":
            default_sections = [
                ("navbar", DEFAULT_SECTION_CONTENTS["navbar"]),
                ("hero", {**DEFAULT_SECTION_CONTENTS["hero"], "title": title}),
                ("progress", DEFAULT_SECTION_CONTENTS["progress"]),
                ("about", DEFAULT_SECTION_CONTENTS["about"]),
                ("cta", DEFAULT_SECTION_CONTENTS["cta"]),
                ("footer", DEFAULT_SECTION_CONTENTS["footer"])
            ]

            for idx, (s_type, s_content) in enumerate(default_sections, start=1):
                sec = Section(
                    page_id=page.id,
                    type=s_type,
                    order=idx,
                    content=s_content
                )
                db.session.add(sec)

            db.session.commit()
            flash("Campaign berhasil dibuat menggunakan template!", "success")
            return redirect(f"/{page.slug}")

        db.session.commit()
        flash("Campaign berhasil dibuat! Silakan tambahkan section secara manual.", "success")
        return redirect(url_for("admin.manage_sections_manual", page_id=page.id))

    return render_template("admin/new_page.html")


@admin_bp.route("/page/<int:page_id>/toggle-publish", methods=["POST"])
@login_required
def toggle_publish(page_id):
    page = Page.query.get_or_404(page_id)
    page.is_published = not page.is_published
    db.session.commit()

    status = "Published" if page.is_published else "Draft"
    flash(f"Status diubah menjadi {status}", "success")
    return redirect(url_for("admin.list_pages"))


@admin_bp.route("/page/<int:page_id>/delete", methods=["POST"])
@login_required
def delete_page(page_id):
    page = Page.query.get_or_404(page_id)

    Section.query.filter_by(page_id=page.id).delete()
    db.session.delete(page)
    db.session.commit()

    flash(f"Campaign '{page.title}' berhasil dihapus!", "success")
    return redirect(url_for("admin.list_pages"))


# ==============================================================================
# 4. SECTIONS MANAGEMENT (Form Based - Manual)
# ==============================================================================

@admin_bp.route("/page/<int:page_id>/sections-manual")
@login_required
def manage_sections_manual(page_id):
    page = Page.query.get_or_404(page_id)
    return render_template("admin/manage_sections_manual.html", page=page)


@admin_bp.route("/page/<int:page_id>/add-section", methods=["POST"])
@login_required
def add_section(page_id):
    page = Page.query.get_or_404(page_id)
    section_type = request.form.get("type")

    if not section_type:
        flash("Jenis section wajib dipilih", "danger")
        return redirect(url_for("admin.manage_sections_manual", page_id=page.id))

    last_order = db.session.query(db.func.max(Section.order)).filter_by(page_id=page.id).scalar() or 0

    # Ambil nilai default berdasarkan tipe section
    initial_content = DEFAULT_SECTION_CONTENTS.get(section_type, {"title": section_type.title()})

    section = Section(
        page_id=page.id,
        type=section_type,
        order=last_order + 1,
        content=initial_content
    )
    db.session.add(section)
    db.session.commit()

    flash(f"Section '{section_type}' berhasil ditambahkan", "success")
    return redirect(url_for("admin.edit_section", section_id=section.id))


def save_uploaded_file(file):
    if file and file.filename != '':
        # Ambil ekstensi berkas
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()

        # Buat nama unik agar tidak saling menimpa
        unique_filename = f"{uuid.uuid4().hex}{ext}"

        # Folder tujuan: app/static/uploads/
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        # Mengembalikan path publik untuk template
        return f"/static/uploads/{unique_filename}"
    return None


@admin_bp.route("/section/<int:section_id>/edit", methods=["GET", "POST"])
@login_required
def edit_section(section_id):
    section = Section.query.get_or_404(section_id)
    page = section.page

    if request.method == "POST":
        content = dict(section.content or {})

        # 1. Simpan input text/textarea biasa
        for key, value in request.form.items():
            if key != "csrf_token":
                content[key] = value

        # 2. Proses upload file dari device (jika ada)
        for key, file in request.files.items():
            if file and file.filename != '':
                file_url = save_uploaded_file(file)
                if file_url:
                    # Menghilangkan akhiran '_file' untuk nama key di JSON content
                    # Contoh: 'logo_url_file' -> 'logo_url'
                    field_key = key.replace('_file', '')
                    content[field_key] = file_url

        section.content = content
        flag_modified(section, "content")

        section.updated_at = datetime.utcnow()
        page.updated_at = datetime.utcnow()
        db.session.commit()

        flash("Section berhasil disimpan", "success")
        return redirect(url_for("admin.manage_sections_manual", page_id=page.id))

    return render_template("admin/edit_section.html", section=section, page=page)


@admin_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)
    page_id = section.page_id

    db.session.delete(section)
    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success", "message": "Section berhasil dihapus"})

    flash("Section berhasil dihapus", "success")
    return redirect(url_for("admin.manage_sections_manual", page_id=page_id))


@admin_bp.route("/page/<int:page_id>/reorder", methods=["POST"])
@login_required
def reorder_sections(page_id):
    page = Page.query.get_or_404(page_id)
    order_data = request.json.get("order", [])

    for item in order_data:
        section = Section.query.filter_by(id=item["id"], page_id=page.id).first()
        if section:
            section.order = item["order"]

    db.session.commit()
    return jsonify({"status": "ok"})


# ==============================================================================
# 5. LIVE EDIT & FRONTEND API MANAGEMENT
# ==============================================================================

@admin_bp.route("/page/<int:page_id>/add-section-live", methods=["POST"])
@login_required
def add_section_live(page_id):
    page = Page.query.get_or_404(page_id)
    section_type = request.form.get("type")

    if section_type:
        last_order = db.session.query(db.func.max(Section.order)).filter_by(page_id=page.id).scalar() or 0
        initial_content = DEFAULT_SECTION_CONTENTS.get(section_type, {"title": section_type.title()})

        section = Section(
            page_id=page.id,
            type=section_type,
            order=last_order + 1,
            content=initial_content
        )
        db.session.add(section)
        db.session.commit()
        flash(f"Section '{section_type}' berhasil ditambahkan!", "success")

    return redirect(f"/{page.slug}")


@admin_bp.route("/api/live-edit", methods=["POST"])
@login_required
def live_edit_sections():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Payload JSON kosong"}), 400

        sections_data = data.get("sections", [])

        for item in sections_data:
            section_id = item.get("id")
            content_updates = item.get("content", {})

            section = Section.query.get(section_id)
            if section:
                current_content = dict(section.content or {})
                for key, value in content_updates.items():
                    current_content[key] = value

                section.content = current_content
                flag_modified(section, "content")  # Menandai field JSON telah berubah
                section.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"status": "success", "message": "Berhasil disimpan!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
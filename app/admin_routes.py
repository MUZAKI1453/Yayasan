import os
import re
import uuid
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.orm.attributes import flag_modified

from app.models import User, Page, Section
from app.extensions import db

admin_bp = Blueprint("admin", __name__)

# ==============================================================================
# DEFAULT SECTION CONTENTS (UNUK ADD SECTION SINGLE MANUAL)
# ==============================================================================
DEFAULT_SECTION_CONTENTS = {
    "navbar": {
        "brand_name": "SDIP Baitussalam",
        "logo_url": "",
        "nav_theme": "bg-white navbar-light shadow-sm",
        "nav_position": "sticky-top",
        "nav_text_1": "Beranda", "nav_url_1": "#beranda",
        "button_text_1": "Daftar PPDB", "button_link_1": "#ppdb"
    },
    "hero": {
        "eyebrow": "Penerimaan Peserta Didik Baru (PPDB)",
        "title": "Membentuk Generasi Rabbani",
        "subtitle": "Selamat datang di sekolah kami...",
        "button_text": "Daftar Sekarang",
        "button_link": "#ppdb"
    },
    "about": {
        "eyebrow": "Profil",
        "title": "Tentang Kami",
        "content": "Tuliskan deskripsi/profil di sini..."
    },
    "features": {
        "title": "Keunggulan Kami",
        "item1_title": "Fasilitas Lengkap", "item1_desc": "Ruang belajar nyaman & AC."
    },
    "donation_campaign": {
        "eyebrow": "Program Wakaf & Infaq",
        "title": "Pembangunan Gedung Ruang Kelas Baru",
        "subtitle": "Mari dukung sarana belajar siswa.",
        "target": 500000000, "collected": 0,
        "bank_account": "BSI: 7123-4567-89 a.n. YPI Baitussalam"
    },
    "progress": {
        "title": "Progress Kuota",
        "target": 60, "collected": 0
    },
    "gallery": {
        "title": "Galeri Dokumentasi"
    },
    "testimonial": {
        "title": "Testimoni Orang Tua"
    },
    "faq": {
        "title": "Pertanyaan Umum (FAQ)"
    },
    "cta": {
        "title": "Segera Daftarkan Putra-Putri Anda",
        "button_text": "Daftar Sekarang", "button_link": "#ppdb"
    },
    "footer": {
        "copyright": "© 2026 SDIP Baitussalam. All rights reserved."
    }
}

# ==============================================================================
# PRESET TEMPLATE DEFINITIONS (FULL PAGE SECTIONS GENERATOR)
# ==============================================================================
PRESET_TEMPLATES = {
    # 1. Template PPDB & Sekolah
    "template_ppdb": [
        ("navbar", {
            "brand_name": "SDIP Baitussalam",
            "logo_url": "",
            "nav_theme": "bg-white navbar-light shadow-sm",
            "nav_position": "sticky-top",
            "nav_text_1": "Beranda", "nav_url_1": "#beranda",
            "nav_text_2": "Profil", "nav_url_2": "#profil",
            "nav_text_3": "Fasilitas", "nav_url_3": "#fasilitas",
            "button_text_1": "Daftar PPDB", "button_link_1": "#ppdb"
        }),
        ("hero", {
            "eyebrow": "Penerimaan Peserta Didik Baru (PPDB) 2026/2027",
            "title": "Membentuk Generasi Rabbani Berakhlaq & Berprestasi",
            "subtitle": "Selamat datang di SDIP Baitussalam. Sekolah Dasar Islam Terpadu dengan lingkungan belajar yang asri dan berkarakter.",
            "button_text": "Daftar Sekarang",
            "button_link": "#ppdb",
            "background_image": ""
        }),
        ("about", {
            "eyebrow": "Profil Sekolah",
            "title": "Tentang SDIP Baitussalam",
            "content": "Kami berkomitmen menyelenggarakan pendidikan Islam terpadu berkualitas, meletakkan dasar keimanan, adab, serta penguasaan sains dan ilmu pengetahuan umum.",
            "image": "",
            "image_caption": "Gedung Pembelajaran & Lingkungan Sekolah"
        }),
        ("features", {
            "title": "Keunggulan Sekolah Kami",
            "subtitle": "Mengapa memilih SDIP Baitussalam untuk putra-putri Anda?",
            "item1_title": "Program Tahfidz", "item1_desc": "Target hafalan Juz 30 dan surah-surah pilihan.",
            "item2_title": "Pengajar Berpengalaman", "item2_desc": "Guru-guru profesional, sabar, dan berdedikasi.",
            "item3_title": "Fasilitas Lengkap", "item3_desc": "Ruang kelas AC, lab komputer, dan lapangan olahraga.",
            "item4_title": "Pembiasaan Adab Islami", "item4_desc": "Pembiasaan sholat berjamaah & dzikir harian."
        }),
        ("progress", {
            "title": "Kuota Pendaftaran Siswa Baru",
            "target": 60,
            "collected": 42,
            "extra_text": "Sisa kuota pendaftaran terbatas untuk gelombang ini!"
        }),
        ("gallery", {
            "title": "Galeri Kegiatan & Lingkungan Sekolah",
            "subtitle": "Dokumentasi suasana belajar dan aktivitas siswa",
            "image1": "", "image2": "", "image3": ""
        }),
        ("testimonial", {
            "title": "Apa Kata Orang Tua Siswa",
            "name1": "Bapak Ahmad", "role1": "Orang Tua Kelas 3",
            "quote1": "Alhamdulillah hafalan Al-Qur'an anak berkembang pesat.",
            "name2": "Ibu Siti", "role2": "Orang Tua Alumni",
            "quote2": "Sekolah yang sangat memperhatikan perkembangan karakter anak."
        }),
        ("faq", {
            "title": "Pertanyaan Umum (FAQ PPDB)",
            "faq_q1": "Kapan pendaftaran PPDB dibuka?",
            "faq_a1": "Pendaftaran dibuka setiap gelombang mulai bulan November.",
            "faq_q2": "Apa saja syarat pendaftarannya?",
            "faq_a2": "Fotokopi Akta Kelahiran, KK, Pas Foto, dan mengisi formulir online."
        }),
        ("cta", {
            "title": "Segera Daftarkan Putra-Putri Anda!",
            "subtitle": "Masa depan cerah berawal dari pendidikan dasar yang berkualitas dan berkarakter.",
            "button_text": "Isi Formulir PPDB",
            "button_link": "#ppdb"
        }),
        ("footer", {
            "copyright": "© 2026 SDIP Baitussalam. All rights reserved.",
            "description": "Lembaga Pendidikan Islam Terpadu & Pembentukan Karakter Rabbani.",
            "facebook": "#", "instagram": "#", "whatsapp": "#"
        })
    ],

    # 2. Template Profil Yayasan Utama
    "template_yayasan": [
        ("navbar", {
            "brand_name": "YPI Baitussalam",
            "logo_url": "",
            "nav_theme": "bg-dark navbar-dark",
            "nav_position": "sticky-top",
            "nav_text_1": "Profil", "nav_url_1": "#profil",
            "nav_text_2": "Unit Pendidikan", "nav_url_2": "#unit",
            "button_text_1": "Hubungi Kami", "button_link_1": "#kontak"
        }),
        ("hero", {
            "eyebrow": "Yayasan Pendidikan Islam",
            "title": "Mewujudkan Lembaga Pendidikan Islam Unggul & Terpercaya",
            "subtitle": "Mengelola unit pendidikan dari jenjang PAUD, SDIP, hingga SMPI untuk mencetak generasi Qur'ani.",
            "button_text": "Pelajari Selengkapnya",
            "button_link": "#profil"
        }),
        ("about", {
            "eyebrow": "Visi & Misi Yayasan",
            "title": "Pengabdian Untuk Pendidikan Umat",
            "content": "YPI Baitussalam hadir sebagai wadah pembina generasi muda Islam yang berilmu, berakhlak mulia, dan siap berkontribusi bagi masyarakat.",
            "image": ""
        }),
        ("features", {
            "title": "Unit Pendidikan Yang Dinaungi",
            "subtitle": "Layanan pendidikan berjenjang di bawah naungan yayasan",
            "item1_title": "PAUD & TK Islam", "item1_desc": "Pendidikan anak usia dini berbasis adab.",
            "item2_title": "SDIP Baitussalam", "item2_desc": "Sekolah dasar Islam terpadu kurikulum plus.",
            "item3_title": "SMPI Baitussalam", "item3_desc": "Sekolah menengah dengan penguatan ilmu & tahfidz."
        }),
        ("cta", {
            "title": "Bersama Membangun Masa Depan Pendidikan Islam",
            "subtitle": "Silakan hubungi sekretariat yayasan untuk informasi lebih lanjut.",
            "button_text": "Kontak Yayasan",
            "button_link": "#kontak"
        }),
        ("footer", {
            "copyright": "© 2026 Yayasan Pendidikan Islam Baitussalam.",
            "description": "Pusat Pengelolaan Pendidikan Islam Terpadu.",
            "facebook": "#", "instagram": "#", "whatsapp": "#"
        })
    ],

    # 3. Template Donasi & Wakaf Pembangunan
    "template_donasi": [
        ("navbar", {
            "brand_name": "Wakaf Baitussalam",
            "logo_url": "",
            "nav_theme": "bg-white navbar-light shadow-sm",
            "nav_position": "sticky-top",
            "nav_text_1": "Program", "nav_url_1": "#program",
            "button_text_1": "Infaq Sekarang", "button_link_1": "#donasi"
        }),
        ("hero", {
            "eyebrow": "Program Wakaf Pembangunan 2026",
            "title": "Galang Donasi Pembangunan Ruang Kelas & Gedung Baru",
            "subtitle": "Mari berinvestasi akhirat dengan mendukung sarana belajar para penghafal Al-Qur'an dan siswa dhuafa.",
            "button_text": "Salurkan Wakaf / Donasi",
            "button_link": "#donasi"
        }),
        ("donation_campaign", {
            "eyebrow": "Target Pembangunan Gedung",
            "title": "Pembangunan Gedung Laboratorium & Ruang Belajar Baru",
            "subtitle": "Urgensi dana digunakan untuk pembebasan lahan & pengerjaan struktur lantai 2.",
            "target": 500000000,
            "collected": 125000000,
            "bank_account": "BSI: 7123-4567-89 a.n. YPI Baitussalam Wakaf",
            "button_text": "Konfirmasi Transfer Donasi",
            "button_link": "#donasi"
        }),
        ("faq", {
            "title": "Pertanyaan Donatur (FAQ)",
            "faq_q1": "Bagaimana cara menyalurkan donasi?",
            "faq_a1": "Transfer via rekening resmi yayasan lalu kirim bukti transfer.",
            "faq_q2": "Apakah ada laporan penggunaan dana?",
            "faq_a2": "Ya, laporan keuangan diperbarui berkala di website resmi."
        }),
        ("footer", {
            "copyright": "© 2026 YPI Baitussalam Fundraising.",
            "description": "Lembaga Resmi Pengelolaan Infaq & Wakaf Pendidikan.",
            "facebook": "#", "instagram": "#", "whatsapp": "#"
        })
    ]
}


def save_uploaded_file(file):
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        return f"/static/uploads/{unique_filename}"
    return None


# ==============================================================================
# 1. AUTHENTICATION
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
# 3. PAGES (CAMPAIGN / PROFILE) MANAGEMENT
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
        template_id = request.form.get("template_id", "template_ppdb")

        if not title:
            flash("Judul halaman wajib diisi!", "danger")
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

        # Ambil susunan section berdasarkan preset template yang dipilih
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
        flash("Halaman berhasil dibuat! Silakan sesuaikan teks & foto langsung di bawah ini.", "success")

        # Alihkan langsung ke halaman Live Editor Full-Page
        return redirect(f"/{page.slug}")

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

    flash(f"Halaman '{page.title}' berhasil dihapus!", "success")
    return redirect(url_for("admin.list_pages"))


# ==============================================================================
# 4. SECTIONS MANAGEMENT (MANUAL)
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


@admin_bp.route("/section/<int:section_id>/edit", methods=["GET", "POST"])
@login_required
def edit_section(section_id):
    section = Section.query.get_or_404(section_id)
    page = section.page

    if request.method == "POST":
        content = dict(section.content or {})

        # Simpan input text
        for key, value in request.form.items():
            if key != "csrf_token":
                content[key] = value

        # Upload file dari device
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

        flash("Section berhasil disimpan!", "success")
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
# 5. LIVE EDIT & FRONTEND API
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
                flag_modified(section, "content")
                section.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"status": "success", "message": "Berhasil disimpan!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500



# ==============================================================================
# 6. LIVE EDIT ADVANCED API (UPLOAD GAMBAR, GANTI WARNA, TOMBOL)
# ==============================================================================

@admin_bp.route("/api/live-upload-image", methods=["POST"])
@login_required
def live_upload_image():
    """API untuk upload gambar/logo secara instant dari halaman frontend"""
    try:
        section_id = request.form.get("section_id")
        field_name = request.form.get("field_name")  # misal: 'logo_url', 'image', 'background_image'
        file = request.files.get("image_file")

        if not section_id or not field_name or not file:
            return jsonify({"status": "error", "message": "Parameter tidak lengkap"}), 400

        section = Section.query.get_or_404(section_id)
        file_url = save_uploaded_file(file)

        if not file_url:
            return jsonify({"status": "error", "message": "Gagal menyimpan file"}), 400

        # Update JSON content section
        content = dict(section.content or {})
        content[field_name] = file_url
        section.content = content
        flag_modified(section, "content")
        section.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Gambar berhasil diunggah!",
            "file_url": file_url
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_bp.route("/api/live-update-style", methods=["POST"])
@login_required
def live_update_style():
    """API untuk ganti warna background/tema, teks tombol, & link tombol"""
    try:
        data = request.get_json()
        section_id = data.get("section_id")
        updates = data.get("updates", {}) # misal: {"nav_theme": "bg-dark navbar-dark", "button_link": "#ppdb"}

        if not section_id:
            return jsonify({"status": "error", "message": "Section ID wajib diisi"}), 400

        section = Section.query.get_or_404(section_id)
        content = dict(section.content or {})

        for key, val in updates.items():
            content[key] = val

        section.content = content
        flag_modified(section, "content")
        section.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"status": "success", "message": "Pengaturan section berhasil diperbarui!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
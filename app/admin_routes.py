import re
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app.models import User, Page, Section
from app.extensions import db

admin_bp = Blueprint("admin", __name__)


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

        # 1. Cek validasi input
        if not username or not password:
            flash("Username dan password wajib diisi!", "warning")
            return render_template("admin/login.html")

        # 2. Cek keberadaan user dan kecocokan password
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
        if not title:
            flash("Judul wajib diisi", "danger")
            return redirect(url_for("admin.new_page"))

        # Generate slug otomatis
        slug = re.sub(r"[^a-z0-9-]", "-", title.lower()).strip("-")
        base_slug = slug
        counter = 1

        # Pastikan slug unik
        while Page.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Buat page dan otomatis ter-publish
        page = Page(title=title, slug=slug, is_published=True)
        db.session.add(page)
        db.session.commit()

        flash("Campaign berhasil dibuat dan otomatis dipublikasikan!", "success")
        return redirect(f"/{page.slug}")  # Direct ke live-edit

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

    # Hapus semua section terkait terlebih dahulu
    Section.query.filter_by(page_id=page.id).delete()

    # Hapus page
    db.session.delete(page)
    db.session.commit()

    flash(f"Campaign '{page.title}' berhasil dihapus!", "success")
    return redirect(url_for("admin.list_pages"))


# ==============================================================================
# 4. SECTIONS MANAGEMENT (Form Based)
# ==============================================================================

@admin_bp.route("/page/<int:page_id>/sections")
@login_required
def manage_sections(page_id):
    page = Page.query.get_or_404(page_id)
    return render_template("admin/manage_sections.html", page=page)


@admin_bp.route("/page/<int:page_id>/add-section", methods=["POST"])
@login_required
def add_section(page_id):
    page = Page.query.get_or_404(page_id)
    section_type = request.form.get("type")

    if not section_type:
        flash("Jenis section wajib dipilih", "danger")
        return redirect(url_for("admin.manage_sections", page_id=page.id))

    last_order = db.session.query(db.func.max(Section.order)).filter_by(page_id=page.id).scalar() or 0

    section = Section(
        page_id=page.id,
        type=section_type,
        order=last_order + 1,
        content={}
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
        content = {}
        for key, value in request.form.items():
            if key != "csrf_token":
                content[key] = value

        section.content = content
        section.updated_at = datetime.utcnow()
        page.updated_at = datetime.utcnow()
        db.session.commit()

        flash("Section berhasil disimpan", "success")
        return redirect(url_for("admin.manage_sections", page_id=page.id))

    return render_template("admin/edit_section.html", section=section, page=page)


@admin_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)
    page_id = section.page_id

    db.session.delete(section)
    db.session.commit()

    # Handling response untuk Fetch/AJAX Request
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success", "message": "Section berhasil dihapus"})

    flash("Section berhasil dihapus", "success")
    return redirect(url_for("admin.manage_sections", page_id=page_id))


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

        # Template bawaan isi dummy untuk live preview
        default_contents = {
            "hero": {
                "eyebrow": "Campaign Baru",
                "title": "Judul Utama Campaign",
                "subtitle": "Tulis deskripsi singkat di sini...",
                "button_text": "Donasi Sekarang",
                "button_link": "#"
            },
            "progress": {
                "title": "Progress Donasi",
                "target": 100000000,
                "collected": 0,
                "extra_text": "Mari bersama-sama membantu"
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
                "item1_title": "Poin 1", "item1_desc": "Deskripsi poin pertama...",
                "item2_title": "Poin 2", "item2_desc": "Deskripsi poin kedua...",
                "item3_title": "Poin 3", "item3_desc": "Deskripsi poin ketiga...",
                "item4_title": "Poin 4", "item4_desc": "Deskripsi poin keempat..."
            },
            "gallery": {
                "title": "Galeri Dokumentasi",
                "subtitle": "Foto kegiatan terkait",
                "image1": "",
                "image2": ""
            },
            "testimonial": {
                "title": "Testimoni Donatur",
                "name1": "Hamba Allah", "role1": "Donatur", "quote1": "Semoga amanah dan bermanfaat.",
                "name2": "Ibu Dermawan", "role2": "Donatur", "quote2": "Senang bisa membantu sesama.",
                "name3": "Anak Sholeh", "role3": "Donatur", "quote3": "Terima kasih atas kerja kerasnya."
            },
            "cta": {
                "title": "Mari Bersama Membantu",
                "subtitle": "Ulurkan tangan Anda untuk kebaikan",
                "button_text": "Donasi Sekarang",
                "button_link": "#"
            }
        }

        initial_content = default_contents.get(section_type, {"title": "Section Baru"})

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
                section.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"status": "success", "message": "Berhasil disimpan!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# ==============================================================================
# TEMPLATE PRESETS (Untuk Klien Non-Teknis)
# ==============================================================================
PRESET_TEMPLATES = {
    "wakaf_pembangunan": {
        "title": "Wakaf Pembangunan Gedung Ruang Kelas",
        "sections": [
            {
                "type": "hero",
                "content": {
                    "eyebrow": "YPI Baitussalam • Program Wakaf",
                    "title": "Mari Tabung Amal Jariah Lewat Pembangunan Ruang Kelas Santri",
                    "subtitle": "Pahala tak terputus dengan menghadirkan fasilitas belajar yang layak dan nyaman bagi generasi penghafal Al-Qur'an.",
                    "button_text": "Wakaf Sekarang",
                    "button_link": "#donasi",
                    "bg_image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?auto=format&fit=crop&w=1200&q=80"
                }
            },
            {
                "type": "progress",
                "content": {
                    "title": "Capaian Dana Wakaf",
                    "target": 250000000,
                    "collected": 85000000,
                    "extra_text": "Dibutuhkan Rp 165.000.000 lagi untuk menyelesaikan tahap pencetus struktur dasar."
                }
            },
            {
                "type": "about",
                "content": {
                    "eyebrow": "Latar Belakang",
                    "title": "Mengapa Program Ini Penting?",
                    "content": "Seiring bertambahnya jumlah santri dan murid baru di Yayasan Pendidikan Islam Baitussalam, kapasitas kelas yang ada saat ini sudah tidak mencukupi. Melalui program wakaf ini, kita bersama-sama membangun gedung 2 lantai...",
                    "image": "https://images.unsplash.com/photo-1588072432836-e10032774350?auto=format&fit=crop&w=800&q=80",
                    "image_caption": "Rancangan maket pembangunan ruang kelas baru YPI Baitussalam"
                }
            },
            {
                "type": "cta",
                "content": {
                    "title": "Salurkan Wakaf Terbaik Anda Hari Ini",
                    "subtitle": "Setiap bata yang terpasang menjadi saksi kebaikan Anda di akhirat kelak.",
                    "button_text": "Konfirmasi Wakaf via WhatsApp",
                    "button_link": "https://wa.me/6281234567890?text=Assalamu'alaikum,%20saya%20ingin%20berwakaf"
                }
            }
        ]
    },
    "ppdb_beasiswa": {
        "title": "Penerimaan Santri Baru & Beasiswa Yatim",
        "sections": [
            {
                "type": "hero",
                "content": {
                    "eyebrow": "PPDB & Orang Tua Asuh",
                    "title": "Bantu Beasiswa Pendidikan Santri Yatim & Dhuafa",
                    "subtitle": "Mencetak generasi Rabbani yang berakhlak mulia, berprestasi, dan mandiri.",
                    "button_text": "Daftar / Jadi Donatur",
                    "button_link": "#donasi",
                    "bg_image": "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=1200&q=80"
                }
            },
            {
                "type": "features",
                "content": {
                    "title": "Keunggulan Pendidikan YPI Baitussalam",
                    "subtitle": "Kurikulum terpadu sains dan keislaman",
                    "item1_title": "Tahfidz Al-Qur'an", "item1_desc": "Target hafalan 30 Juz dengan tajwid yang shahih.",
                    "item2_title": "Pendidikan Karakter", "item2_desc": "Pembiasaan adab dan akhlakul karimah sehari-hari.",
                    "item3_title": "Fasilitas Lengkap", "item3_desc": "Laboratorium komputer, perpustakaan, dan area olahraga.",
                    "item4_title": "Tenaga Pengajar Kompeten", "item4_desc": "Lulusan perguruan tinggi Islam ternama & berpengalaman."
                }
            }
        ]
    }
}


# --- ROUTE TAMBAHAN UNTUK APLIKASI PRESET TEMPLATE ---
@admin_bp.route("/page/<int:page_id>/apply-preset/<preset_key>", methods=["POST"])
@login_required
def apply_preset(page_id, preset_key):
    page = Page.query.get_or_404(page_id)
    preset = PRESET_TEMPLATES.get(preset_key)

    if not preset:
        flash("Preset template tidak ditemukan!", "danger")
        return redirect(url_for("admin.manage_sections", page_id=page.id))

    # Hapus section lama jika ada
    Section.query.filter_by(page_id=page.id).delete()

    # Masukkan section preset baru
    for index, sec_data in enumerate(preset["sections"], start=1):
        section = Section(
            page_id=page.id,
            type=sec_data["type"],
            order=index,
            content=sec_data["content"]
        )
        db.session.add(section)

    db.session.commit()
    flash(f"Template '{preset['title']}' berhasil diterapkan!", "success")
    return redirect(f"/{page.slug}")


# ==============================================================================
# ROUTE LIVE EDIT DENGAN DUKUNGAN API BARU
# ==============================================================================
@admin_bp.route("/page/<int:page_id>/save-live-edit", methods=["POST"])
@login_required
def save_live_edit(page_id):
    page = Page.query.get_or_404(page_id)
    data = request.get_json()

    if not data or "sections" not in data:
        return jsonify({"status": "error", "message": "Data tidak valid"}), 400

    try:
        for item in data["sections"]:
            sec_id = item.get("section_id")
            content_updates = item.get("content", {})

            section = Section.query.filter_by(id=sec_id, page_id=page.id).first()
            if section:
                # Merge data lama dengan data baru
                updated_content = dict(section.content or {})
                updated_content.update(content_updates)
                section.content = updated_content
                section.updated_at = datetime.utcnow()

        page.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"status": "success", "message": "Halaman berhasil diperbarui!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
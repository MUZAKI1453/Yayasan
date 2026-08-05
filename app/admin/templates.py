# app/admin/templates.py
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from app.models import Section

SECTION_NAV_NAMES = {
    "hero": "Beranda",
    "about": "Profil",
    "features": "Keunggulan",
    "donation_campaign": "Donasi",
    "progress": "Progress",
    "gallery": "Galeri",
    "testimonial": "Testimoni",
    "faq": "FAQ",
    "cta": "PPDB"
}

DEFAULT_SECTION_CONTENTS = {
    "navbar": {
        "brand_name": "SDIP Baitussalam",
        "logo_url": "",
        "nav_theme": "bg-white navbar-light shadow-sm",
        "nav_position": "sticky-top",
        "button_text_1": "Daftar PPDB",
        "button_link_1": "#ppdb"
    },
    "hero": {
        "eyebrow": "Penerimaan Peserta Didik Baru (PPDB)",
        "title": "Membentuk Generasi Rabbani",
        "subtitle": "Selamat datang di sekolah kami...",
        "button_text": "Daftar Sekarang",
        "button_link": "#ppdb",
        "bg_image": ""
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
        "title": "Testimoni Orang Tua",
        "quote1": "Alhamdulillah sekolahnya sangat bagus dan membimbing.",
        "name1": "Bapak Ahmad",
        "role1": "Orang Tua Siswa",
        "quote2": "Fasilitas lengkap dan pengajarnya ramah.",
        "name2": "Ibu Fatimah",
        "role2": "Orang Tua Alumni"
    },
    "faq": {
        "title": "Pertanyaan Umum (FAQ)"
    },
    "cta": {
        "title": "Segera Daftarkan Putra-Putri Anda",
        "button_text": "Daftar Sekarang", "button_link": "#ppdb"
    },
    "footer": {
        "title": "SDIP Baitussalam",
        "description": "Lembaga pendidikan Islam terpadu unggulan.",
        "address": "Jl. Pendidikan No. 123, Bandung",
        "phone": "+62 812-3456-7890",
        "facebook_url": "https://facebook.com",
        "instagram_url": "https://instagram.com",
        "whatsapp_number": "6281234567890",
        "maps_embed_url": "",
        "copyright": "© 2026 SDIP Baitussalam. All rights reserved."
    }
}

PRESET_TEMPLATES = {
    "template_ppdb": ["navbar", "hero", "about", "features", "progress", "gallery", "testimonial", "faq", "cta",
                      "footer"],
    "template_yayasan": ["navbar", "hero", "about", "features", "cta", "footer"],
    "template_donasi": ["navbar", "hero", "donation_campaign", "faq", "footer"]
}


def generate_nav_items_for_page(page_id):
    """
    Fungsi Reaktif: Membaca seluruh section yang ada di database untuk halaman tertentu,
    lalu menghasilkan list nav_items (mengabaikan navbar & footer).
    """
    sections = Section.query.filter_by(page_id=page_id).order_by(Section.order.asc()).all()
    nav_items = []

    for sec in sections:
        # PENGECUALIAN: Navbar & Footer tidak dibuatkan tombol menu di navbar
        if sec.type in ["navbar", "footer"]:
            continue

        content = sec.content or {}
        nav_id = content.get("nav_id")

        # Jika section lama belum punya nav_id, buatkan secara otomatis
        if not nav_id:
            nav_id = f"sec_{uuid.uuid4().hex[:8]}"
            content["nav_id"] = nav_id
            sec.content = content

        nav_text = SECTION_NAV_NAMES.get(sec.type, sec.type.capitalize())
        nav_items.append({
            "text": nav_text,
            "url": f"#{nav_id}"
        })

    return nav_items


def get_preset_sections(preset_key):
    """
    Menghasilkan list tuple (section_type, content_dict) saat awal pembuatan campaign baru.
    """
    section_types = PRESET_TEMPLATES.get(preset_key, PRESET_TEMPLATES["template_ppdb"])

    generated_sections = []
    nav_items = []
    section_instances = []

    for sec_type in section_types:
        content = DEFAULT_SECTION_CONTENTS.get(sec_type, {}).copy()

        # PENGECUALIAN: Footer & Navbar diabaikan dari daftar tombol menu
        if sec_type not in ["navbar", "footer"]:
            nav_id = f"sec_{uuid.uuid4().hex[:8]}"
            content["nav_id"] = nav_id

            nav_text = SECTION_NAV_NAMES.get(sec_type, sec_type.capitalize())
            nav_items.append({
                "text": nav_text,
                "url": f"#{nav_id}"
            })

        section_instances.append((sec_type, content))

    for sec_type, content in section_instances:
        if sec_type == "navbar":
            content["nav_items"] = nav_items
        generated_sections.append((sec_type, content))

    return generated_sections


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
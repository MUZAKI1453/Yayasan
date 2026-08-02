# app/admin/templates.py
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

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
        "copyright": "© 2026 SDIP Baitussalam. All rights reserved."
    }
}

PRESET_TEMPLATES = {
    "template_ppdb": [
        ("navbar", DEFAULT_SECTION_CONTENTS["navbar"]),
        ("hero", DEFAULT_SECTION_CONTENTS["hero"]),
        ("about", DEFAULT_SECTION_CONTENTS["about"]),
        ("features", DEFAULT_SECTION_CONTENTS["features"]),
        ("progress", DEFAULT_SECTION_CONTENTS["progress"]),
        ("gallery", DEFAULT_SECTION_CONTENTS["gallery"]),
        ("testimonial", DEFAULT_SECTION_CONTENTS["testimonial"]),
        ("faq", DEFAULT_SECTION_CONTENTS["faq"]),
        ("cta", DEFAULT_SECTION_CONTENTS["cta"]),
        ("footer", DEFAULT_SECTION_CONTENTS["footer"])
    ],
    "template_yayasan": [
        ("navbar", DEFAULT_SECTION_CONTENTS["navbar"]),
        ("hero", DEFAULT_SECTION_CONTENTS["hero"]),
        ("about", DEFAULT_SECTION_CONTENTS["about"]),
        ("features", DEFAULT_SECTION_CONTENTS["features"]),
        ("cta", DEFAULT_SECTION_CONTENTS["cta"]),
        ("footer", DEFAULT_SECTION_CONTENTS["footer"])
    ],
    "template_donasi": [
        ("navbar", DEFAULT_SECTION_CONTENTS["navbar"]),
        ("hero", DEFAULT_SECTION_CONTENTS["hero"]),
        ("donation_campaign", DEFAULT_SECTION_CONTENTS["donation_campaign"]),
        ("faq", DEFAULT_SECTION_CONTENTS["faq"]),
        ("footer", DEFAULT_SECTION_CONTENTS["footer"])
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
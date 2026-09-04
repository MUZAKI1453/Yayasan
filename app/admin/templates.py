import os
import uuid
from flask import current_app, url_for
from werkzeug.utils import secure_filename

# 1. Pemetaan Nama Publik Default berdasarkan Jenis Section
SECTION_NAV_NAMES = {
    "hero": "Beranda",
    "about": "Profil",
    "vision_mission": "Visi & Misi",
    "features": "Keunggulan",
    "donation_campaign": "Donasi",
    "progress": "Progress",
    "gallery": "Galeri",
    "testimonial": "Testimoni",
    "faq": "FAQ",
    "cta": "PPDB"
}

# 2. Konten Default untuk Masing-masing Section
DEFAULT_SECTION_CONTENTS = {
    "navbar": {
        "brand_name": "SDIP Baitussalam",
        "brand_subtitle": "Official Portal",
        "logo_url": "",
        "nav_font_family": "Plus Jakarta Sans",
        "nav_bg_color": "#ffffff",
        "nav_text_color": "dark",
        "button_bg_color": "#2563eb",
        "button_text_color": "#ffffff",
        "button_text_1": "Daftar PPDB",
        "button_link_1": "#sec_cta"
    },
    "hero": {
        "title": "Mulai Langkah Impian Anda Hari Ini",
        "bg_type": "color",
        "bg_color": "#0f172a",
        "bg_image_url": "",
        "subtitle_text": "Solusi terbaik untuk mengembangkan bisnis Anda dengan platform yang fleksibel dan efisien.",
        "subtitle_color": "#94a3b8",
        "subtitle_size": "16",
        "subtitle_font_family": "font-sans",
        "cta_enabled": True,
        "cta_text": "Selengkapnya",
        "cta_url": "#",
        "cta_bg": "#2563eb",
        "cta_color": "#ffffff",
        "cta_font_family": "font-sans",
        "images": [],
        "pos_title_x": "40",
        "pos_title_y": "60",
        "pos_title_w": "500",
        "pos_sub_x": "40",
        "pos_sub_y": "200",
        "pos_sub_w": "480",
        "pos_cta_x": "40",
        "pos_cta_y": "320",
        "pos_img_x": "600",
        "pos_img_y": "50",
        "pos_img_w": "400"
    },
    "about": {
        "eyebrow": "Profil",
        "eyebrow_font_family": "Plus Jakarta Sans",
        "eyebrow_color": "#2563eb",
        "eyebrow_size": "14",
        "title": "Tentang Kami",
        "title_font_family": "Plus Jakarta Sans",
        "title_color": "#0f172a",
        "title_size": "32",
        "subtitle_text": "Tuliskan sub-judul profil di sini...",
        "subtitle": "Tuliskan sub-judul profil di sini...",
        "subtitle_font_family": "Plus Jakarta Sans",
        "subtitle_color": "#475569",
        "subtitle_size": "15",
        "description": "Tuliskan deskripsi lengkap tentang lembaga atau profil di sini...",
        "desc": "Tuliskan deskripsi lengkap tentang lembaga atau profil di sini...",
        "desc_font_family": "Plus Jakarta Sans",
        "desc_color": "#475569",
        "desc_size": "16",
        "bg_type": "color",
        "bg_color": "#ffffff",
        "bg_image_url": "",
        "image_url": "",
        "image_caption": "",
        "cta_enabled": False,
        "cta_text": "Pelajari Lebih Lanjut",
        "cta_url": "#",
        "cta_bg": "#2563eb",
        "cta_color": "#ffffff",
        "cta_font_family": "Plus Jakarta Sans",
        "cta_link_type": "external",
        "cta_target_section_id": "",
        "button": {"text": "", "url": "#"}
    },
    "vision_mission": {
        "eyebrow": "Arah & Tujuan",
        "title": "Visi & Misi Yayasan",
        "subtitle": "Komitmen kami dalam membimbing dan membangun generasi Rabbani.",
        "visi": "Menjadi lembaga pendidikan dan yayasan Islam yang unggul, terpercaya, serta mencetak generasi berakhlaqul karimah.",
        "misi": "<ul class='list-disc list-inside space-y-2 text-slate-600'><li>Menyelenggarakan pendidikan Islam terpadu yang berkualitas.</li><li>Membentuk karakter siswa yang mandiri dan berwawasan luas.</li><li>Mengelola amanah umat secara transparan dan profesional.</li></ul>"
    },
    "features": {
        "title": "Keunggulan Kami",
        "subtitle": "",
        "items": []
    },
    "donation_campaign": {
        "eyebrow": "Program Wakaf & Infaq",
        "title": "Pembangunan Gedung Ruang Kelas Baru",
        "subtitle": "Mari dukung sarana belajar siswa.",
        "target": 500000000,
        "collected": 0,
        "bank_account": "BSI: 7123-4567-89 a.n. YPI Baitussalam"
    },
    "progress": {
        "title": "Progress Kuota",
        "target": 60,
        "collected": 0
    },
    "gallery": {
        "title": "Galeri Dokumentasi",
        "subtitle": "Dokumentasi kegiatan dan fasilitas di lingkungan sekolah kami.",
        "photos": []
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
        "button_text": "Daftar Sekarang",
        "button_link": "#sec_cta"
    },
    "footer": {
        "title": "SDIP Baitussalam",
        "description": "Lembaga pendidikan Islam terpadu unggulan.",
        "address": "Jl. Pendidikan No. 123, Bandung",
        "phone": "+62 812-3456-7890",
        "whatsapp_number": "6281234567890",
        "email": "",
        "facebook_url": "https://facebook.com",
        "instagram_url": "https://instagram.com",
        "youtube_url": "",
        "tiktok_url": "",
        "maps_embed_url": "",
        "copyright": "© 2026 SDIP Baitussalam. All rights reserved."
    }
}

# 3. Susunan Preset Template
PRESET_TEMPLATES = {
    "template_ppdb": ["navbar", "hero", "about", "vision_mission", "features", "progress", "gallery", "testimonial",
                      "faq", "cta", "footer"],
    "template_yayasan": ["navbar", "hero", "about", "vision_mission", "features", "cta", "footer"],
    "template_donasi": ["navbar", "hero", "donation_campaign", "faq", "footer"]
}


def get_preset_sections(preset_key):
    """
    Mengambil daftar (type, content) berdasarkan preset template yang dipilih.
    """
    section_types = PRESET_TEMPLATES.get(preset_key, PRESET_TEMPLATES["template_ppdb"])
    generated_sections = []

    for sec_type in section_types:
        content = DEFAULT_SECTION_CONTENTS.get(sec_type, {}).copy()
        generated_sections.append((sec_type, content))

    return generated_sections


def save_uploaded_file(file):
    """
    Helper untuk menyimpan file gambar yang di-upload ke folder /static/uploads
    """
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        return url_for('static', filename=f'uploads/{unique_filename}')
    return None
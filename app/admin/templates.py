import os
import uuid
from flask import current_app, url_for
from werkzeug.utils import secure_filename
from app.models import Section

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
        "button_link_1": "#sec_cta",
        "nav_items": []
    },
    "hero": {
        "slides": [
            {
                "image": "",
                "eyebrow": "",
                "title": "",
                "subtitle": "",
                "cta": {
                    "text": "",
                    "url": "#"
                }
            }
        ]
    },
    "about": {
        "eyebrow": "Profil",
        "title": "Tentang Kami",
        "description": "Tuliskan deskripsi/profil di sini...",
        "image_url": "",
        "image_caption": "",
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


def generate_nav_items_for_page(page_id):
    """
    Fungsi Reaktif & Hybrid: Membaca seluruh section yang ada di database untuk halaman tertentu,
    lalu menghasilkan list nav_items (mengabaikan navbar & footer) lengkap dengan array children
    untuk dukungan menu dropdown dan tautan halaman internal/eksternal.
    """
    sections = Section.query.filter_by(page_id=page_id).order_by(Section.order.asc()).all()

    # Ambil navbar yang ada jika ada (untuk mempertahankan urutan & custom link yang dibuat user)
    navbar_sec = Section.query.filter_by(page_id=page_id, type="navbar").first()
    existing_items = navbar_sec.content.get("nav_items", []) if (navbar_sec and navbar_sec.content) else []
    existing_map = {item.get("id"): item for item in existing_items if isinstance(item, dict) and item.get("id")}

    nav_items = []

    for sec in sections:
        # PENGECUALIAN: Navbar & Footer tidak dibuatkan tombol menu utama tersendiri secara otomatis
        if sec.type in ["navbar", "footer"]:
            continue

        content = sec.content or {}
        nav_id = content.get("nav_id")

        # Jika section lama belum memiliki nav_id, generate secara otomatis
        if not nav_id:
            nav_id = f"sec_{uuid.uuid4().hex[:8]}"
            content["nav_id"] = nav_id
            sec.content = content

        # Cek jika section ini sudah pernah diatur di navbar sebelumnya
        if nav_id in existing_map:
            item_data = existing_map[nav_id]
            nav_items.append({
                "id": nav_id,
                "text": item_data.get("text", SECTION_NAV_NAMES.get(sec.type, sec.type.title())),
                "url": item_data.get("url", f"#{nav_id}"),
                "children": item_data.get("children", [])
            })
        else:
            # Tentukan teks menu default (Prioritas: title dari content -> SECTION_NAV_NAMES -> format nama type)
            raw_title = content.get("title") or SECTION_NAV_NAMES.get(sec.type, sec.type.replace('_', ' ').title())
            nav_text = SECTION_NAV_NAMES.get(raw_title, raw_title)

            nav_items.append({
                "id": nav_id,
                "text": nav_text,
                "url": f"#{nav_id}",
                "children": []
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

        # PENGECUALIAN: Footer & Navbar diabaikan dari daftar tombol menu otomatis
        if sec_type not in ["navbar", "footer"]:
            nav_id = f"sec_{uuid.uuid4().hex[:8]}"
            content["nav_id"] = nav_id

            nav_text = SECTION_NAV_NAMES.get(sec_type, sec_type.replace('_', ' ').title())
            nav_items.append({
                "id": nav_id,
                "text": nav_text,
                "url": f"#{nav_id}",
                "children": []  # Menyiapkan struktur dropdown
            })

        section_instances.append((sec_type, content))

    for sec_type, content in section_instances:
        if sec_type == "navbar":
            content["nav_items"] = nav_items
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
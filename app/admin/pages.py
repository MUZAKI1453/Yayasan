# app/admin/pages.py
import re
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required
from app.admin import admin_bp
from app.admin.templates import get_preset_sections  # <-- REVISI: Gunakan helper get_preset_sections
from app.models import Page, Section
from app.extensions import db
from sqlalchemy.orm.attributes import flag_modified


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

        # Generate unique slug
        slug = re.sub(r"[^a-z0-9-]", "-", title.lower()).strip("-")
        base_slug = slug
        counter = 1

        while Page.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        page = Page(title=title, slug=slug, is_published=True)
        db.session.add(page)
        db.session.flush()

        # REVISI: Panggil get_preset_sections untuk mendapatkan tuple (s_type, s_content)
        # yang sudah dilengkapi nav_id unik & nav_items otomatis di Navbar
        chosen_template = get_preset_sections(template_id)

        created_sections = []
        for idx, (s_type, s_content) in enumerate(chosen_template, start=1):
            content_copy = dict(s_content)

            if s_type == "hero" and "title" in content_copy:
                content_copy["title"] = title

            sec = Section(page_id=page.id, type=s_type, order=idx, content=content_copy)
            db.session.add(sec)
            created_sections.append((sec, content_copy.get('nav_id')))

        db.session.flush()

        # Konversi preset lama (nav_id/URL #sec_xxx) ke target Section yang stabil.
        navbar = next((sec for sec, _ in created_sections if sec.type == 'navbar'), None)
        if navbar:
            nav_items = (navbar.content or {}).get('nav_items', [])
            legacy_map = {old_id: sec.id for sec, old_id in created_sections if old_id}
            def migrate_items(items):
                result = []
                for item in items or []:
                    item = dict(item)
                    legacy_id = item.get('id')
                    url = str(item.get('url') or '')
                    target = legacy_map.get(legacy_id) or legacy_map.get(url.lstrip('#'))
                    item['target_section_id'] = target
                    target_sec = next((sec for sec, _ in created_sections if sec.id == target), None)
                    item['target_type'] = target_sec.type if target_sec else None
                    item.pop('url', None)
                    item.pop('type', None)
                    item['children'] = migrate_items(item.get('children') or item.get('sub_items') or [])
                    item.pop('sub_items', None)
                    result.append(item)
                return result
            new_content = dict(navbar.content or {})
            new_content['nav_items'] = migrate_items(nav_items)
            new_content['button_enabled'] = bool(new_content.get('button_text_1'))
            button_link = str(new_content.get('button_link_1') or '')
            new_content['button_target_section_id'] = legacy_map.get(button_link.lstrip('#'))
            navbar.content = new_content
            flag_modified(navbar, 'content')

        db.session.commit()

        flash("Campaign berhasil dibuat! Silakan atur isi konten & section di bawah ini.", "success")

        # Redirect langsung ke Visual Editor Split-Screen
        return redirect(url_for("admin.manage_section", page_id=page.id))

    return render_template("admin/new_page.html")


@admin_bp.route("/page/<int:page_id>/toggle-publish", methods=["POST"])
@login_required
def toggle_publish(page_id):
    page = Page.query.get_or_404(page_id)
    page.is_published = not page.is_published
    db.session.commit()
    flash(f"Status diubah menjadi {'Published' if page.is_published else 'Draft'}", "success")
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
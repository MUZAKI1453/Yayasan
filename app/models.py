from datetime import datetime
from app.extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)

    # SEO
    meta_title = db.Column(db.String(70))
    meta_description = db.Column(db.String(160))
    og_image = db.Column(db.String(500))

    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sections = db.relationship(
        "Section",
        backref="page",
        cascade="all, delete-orphan",
        order_by="Section.order"
    )


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("page.id"), nullable=False)

    # Jenis section (hero, progress, about, features, gallery, testimonial, cta, dll)
    type = db.Column(db.String(50), nullable=False)

    # Urutan tampil
    order = db.Column(db.Integer, default=0)

    # Apakah section ditampilkan
    is_active = db.Column(db.Boolean, default=True)

    # Semua data section disimpan dalam JSON (fleksibel)
    # Contoh isi: {"title": "...", "subtitle": "...", "image": "...", "button_text": "..."}
    content = db.Column(db.JSON, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
# app/__init__.py
from flask import Flask
from config import Config
from app.extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"

    # 1. Register Public Routes
    from app.routes import public_bp
    app.register_blueprint(public_bp)

    # 2. Register Admin Blueprint dari package folder 'app/admin'
    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        db.create_all()
        create_default_admin(app)

    return app

def create_default_admin(app):
    from app.models import User
    from config import Config

    # Cek apakah admin sudah ada
    admin = User.query.filter_by(username=Config.DEFAULT_ADMIN_USERNAME).first()
    if not admin:
        admin = User(username=Config.DEFAULT_ADMIN_USERNAME)
        admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print("=" * 50)
        print("✅ ADMIN DEFAULT BERHASIL DIBUAT")
        print(f"   Username : {Config.DEFAULT_ADMIN_USERNAME}")
        print(f"   Password : {Config.DEFAULT_ADMIN_PASSWORD}")
        print("=" * 50)
    else:
        print("ℹ️  Admin sudah ada, skip pembuatan.")
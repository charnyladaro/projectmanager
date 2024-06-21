from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "your_secret_key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project_management.db"
    app.config["UPLOAD_FOLDER"] = "uploads"  # Folder to store uploaded files
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "pdf", "docx"}
    app.config["MAX_CONTENT_PATH"] = 16 * 1024 * 1024  # Max file size 16 M

    db.init_app(app)
    migrate.init_app(app, db)

    UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    with app.app_context():
        from . import models, routes

        db.create_all()

    return app

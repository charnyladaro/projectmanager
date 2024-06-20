from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "your_secret_key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project_management.db"

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from . import models, routes

        db.create_all()

    return app

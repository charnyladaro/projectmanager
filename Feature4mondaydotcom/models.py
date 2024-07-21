from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    send_file,
    send_from_directory,
    abort,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.sql import func
import os
import mimetypes
from functools import wraps
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from sqlalchemy.orm import relationship, declarative_base
from email_validator import validate_email, EmailNotValidError
import uuid
from flask_wtf.file import FileField, FileAllowed
from PIL import Image, ImageDraw, ImageFont
import random
import secrets


basedir = os.path.abspath(os.path.dirname(__file__))
Base = declarative_base()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "project_management.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "capstone"
app.config["MAIL_SERVER"] = "smtp.gmail.com"  # Change this to your email server
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "tmvaptest8@gmail.com"  # Change this to your email
app.config["MAIL_PASSWORD"] = "testPass1"  # Change this to your email password
app.config["MAIL_DEFAULT_SENDER"] = "tmvaptest8@gmail.com"  # Change this to your email
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max-limit
app.config["PROFILE_PICS"] = os.path.join(basedir, "static", "profile_pics")

os.makedirs(app.config["PROFILE_PICS"], exist_ok=True)

csrf = CSRFProtect(app)
db = SQLAlchemy(model_class=declarative_base())
login_manager = LoginManager(app)
login_manager.login_view = "login"
mail = Mail(app)
csrf.init_app(app)
db.init_app(app)
# Models

task_assignments = db.Table(
    "task_assignments",
    db.Column("task_id", db.Integer, db.ForeignKey("task.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class ChatRequest(db.Model):
    __tablename__ = "chat_request"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, server_default=func.now())
    request_type = db.Column(db.String(20), default="chat")  # 'chat' or 'friend'


class Message(db.Model):
    __tablename__ = "messages"  # Explicitly define the table name
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = db.relationship(
        "User", foreign_keys=[receiver_id], backref="received_messages"
    )


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(255), default="default.jpg")
    is_active = db.Column(db.Boolean, default=False)
    assigned_tasks = db.relationship(
        "Task", secondary=task_assignments, back_populates="assigned_users"
    )
    # Update these relationships
    sent_chat_requests = db.relationship(
        "ChatRequest",
        foreign_keys="ChatRequest.sender_id",
        backref="sender",
        lazy="dynamic",
    )
    received_chat_requests = db.relationship(
        "ChatRequest",
        foreign_keys="ChatRequest.receiver_id",
        backref="receiver",
        lazy="dynamic",
    )

    # Add these new relationships for FriendRequest
    sent_friend_requests = db.relationship(
        "FriendRequest",
        foreign_keys="FriendRequest.sender_id",
        backref="friend_request_sender",
        lazy="dynamic",
    )
    received_friend_requests = db.relationship(
        "FriendRequest",
        foreign_keys="FriendRequest.receiver_id",
        backref="friend_request_receiver",
        lazy="dynamic",
    )

    # Keep the friends relationship
    friends = db.relationship(
        "User",
        secondary="friendship",
        primaryjoin=("User.id == friendship.c.user_id"),
        secondaryjoin=("User.id == friendship.c.friend_id"),
        backref="befriended_by",
    )


# Friendship association table
friendship = db.Table(
    "friendship",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("friend_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class EditProfileForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=2, max=20)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("New Password (leave empty to keep current)")
    profile_picture = FileField(
        "Update Profile Picture", validators=[FileAllowed(["jpg", "png"])]
    )
    submit = SubmitField("Update Profile")


class FriendRequest(db.Model):
    __tablename__ = "friend_request"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    __tablename__ = "project"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Task(db.Model):
    __tablename__ = "task"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="To Do")
    due_date = db.Column(db.DateTime)
    time_spent = db.Column(db.Float, default=0)
    files = db.relationship("File", back_populates="task", cascade="all, delete-orphan")
    assigned_users = db.relationship(
        "User", secondary=task_assignments, back_populates="assigned_tasks"
    )


class File(db.Model):
    __tablename__ = "file"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer, db.ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'image' or 'document'
    task = db.relationship("Task", back_populates="files")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    profile_picture = FileField(
        "Profile Picture", validators=[FileAllowed(["jpg", "png", "jpeg", "gif"])]
    )
    submit = SubmitField("Sign Up")

    def validate_email(self, email):
        try:
            valid = validate_email(email.data)
            email.data = valid.email
        except EmailNotValidError as e:
            raise ValidationError(str(e))


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Reset Password")


db.configure_mappers()
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
from models import (
    db,
    User,
    Project,
    Task,
    File,
    ChatRequest,
    Message,
    FriendRequest,
    LoginForm,
    RegistrationForm,
    task_assignments,
    friendship,
)

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
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
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

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    request_type = db.Column(db.String(20), default="chat")  # 'chat' or 'friend'

    # Remove relationships from here


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    files = db.relationship(
        "MessageFile", back_populates="message", cascade="all, delete-orphan"
    )

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = db.relationship(
        "User", foreign_keys=[receiver_id], backref="received_messages"
    )


class MessageFile(db.Model):
    __tablename__ = "message_files"
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("messages.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    message = db.relationship("Message", back_populates="files")


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(255), default="default.jpg")
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
        secondary=friendship,
        primaryjoin=(friendship.c.user_id == id),
        secondaryjoin=(friendship.c.friend_id == id),
        backref=db.backref("befriended_by", lazy="dynamic"),
        lazy="dynamic",
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
    tasks = db.relationship("Task", backref="project", lazy=True)


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
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    task = db.relationship("Task", back_populates="files")


class LoginForm(FlaskForm):
    username = StringField(
        "Username", render_kw={"class": "form-control"}, validators=[DataRequired()]
    )
    password = PasswordField(
        "Password", render_kw={"class": "form-control"}, validators=[DataRequired()]
    )
    submit = SubmitField("Log In", render_kw={"class": "btn btn-primary"})


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username", render_kw={"class": "form-control"}, validators=[DataRequired()]
    )
    email = StringField(
        "Email",
        render_kw={"class": "form-control"},
        validators=[DataRequired(), Email()],
    )
    password = PasswordField(
        "Password", render_kw={"class": "form-control"}, validators=[DataRequired()]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        render_kw={"class": "form-control"},
        validators=[DataRequired(), EqualTo("password")],
    )
    profile_picture = FileField(
        "Profile Picture",
        render_kw={"class": "form-control"},
        validators=[FileAllowed(["jpg", "png", "jpeg", "gif"])],
    )
    submit = SubmitField("Sign Up", render_kw={"class": "btn btn-primary"})

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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/get-csrf-token", methods=["GET"])
def get_csrf_token():
    return jsonify({"csrf_token": generate_csrf()})


# Define allowed extensions
ALLOWED_EXTENSIONS = {
    "txt",
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "xlsm",  # Office documents
    "csv",  # CSV files
    "ppt",
    "pptx",  # PowerPoint
    "zip",
    "rar",  # Compressed files
    "py",
    "js",
    "html",
    "css",  # Code files
}


# Function to check if the file extension is allowed
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You don't have permission to access this page.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route("/")
def index():
    return render_template("index.html")


def create_admin_user():
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", email="admin@example.com", is_admin=True)
            admin.password = generate_password_hash("adminpassword")
            db.session.add(admin)
            print("Admin user created")
        else:
            admin.email = "admin@example.com"  # Update email if needed
            admin.is_admin = True  # Ensure admin status
            admin.password = generate_password_hash("adminpassword")  # Update password
            print("Admin user updated")
        db.session.commit()


@app.route("/profile/<int:user_id>", methods=["GET", "POST"])
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    form = EditProfileForm(obj=user)

    if request.method == "POST" and (
        current_user.is_admin or current_user.id == user.id
    ):
        if form.validate_on_submit():
            user.username = form.username.data
            user.email = form.email.data
            if form.password.data:
                user.password = generate_password_hash(form.password.data)

            if form.profile_picture.data:
                picture_file = save_picture(form.profile_picture.data)
                user.profile_picture = picture_file

            db.session.commit()
            flash("Profile updated successfully", "success")
            return redirect(url_for("user_profile", user_id=user.id))

    is_friend = user in current_user.friends
    can_send_friend_request = not is_friend and user != current_user
    can_chat = is_friend and user != current_user

    return render_template(
        "user_profile.html",
        user=user,
        form=form,
        is_friend=is_friend,
        can_send_friend_request=can_send_friend_request,
        can_chat=can_chat,
    )


@app.route("/make_admin/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def make_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash(f"{user.username} is already an admin.", "info")
    else:
        user.is_admin = True
        db.session.commit()
        flash(f"{user.username} has been made an admin.", "success")
    return redirect(url_for("user_profile", user_id=user_id))


@app.route("/remove_admin/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def remove_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash("You cannot remove your own admin status.", "danger")
    elif not user.is_admin:
        flash(f"{user.username} is not an admin.", "info")
    else:
        user.is_admin = False
        db.session.commit()
        flash(f"Admin status has been removed from {user.username}.", "success")
    return redirect(url_for("user_profile", user_id=user_id))


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        if form.username.data != current_user.username:
            if User.query.filter_by(username=form.username.data).first():
                flash(
                    "That username is taken. Please choose a different one.", "danger"
                )
                return render_template("edit_profile.html", form=form)

        current_user.username = form.username.data
        current_user.email = form.email.data

        if form.password.data:
            current_user.password = generate_password_hash(form.password.data)

        if form.profile_picture.data:
            picture_file = save_picture(form.profile_picture.data)
            current_user.profile_picture = picture_file

        db.session.commit()
        flash("Your account has been updated!", "success")
        return redirect(url_for("user_profile", user_id=current_user.id))

    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    return render_template("edit_profile.html", form=form)


pass


@app.route("/routes")
def list_routes():
    return "\n".join(f"{rule}" for rule in app.url_map.iter_rules())


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, "static/profile_pics", picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


# # Add this function to check allowed file types
def allowed_file4dp(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "png",
        "jpg",
        "jpeg",
        "gif",
    }


def generate_initials_image(username):
    # Get initials
    initials = "".join([name[0] for name in username.split() if name])
    initials = initials[:2].upper()  # Use up to 2 initials

    # Generate a random background color
    bg_color = (
        random.randint(100, 255),
        random.randint(100, 255),
        random.randint(100, 255),
    )

    # Create image
    img = Image.new("RGB", (200, 200), color=bg_color)
    d = ImageDraw.Draw(img)

    # Use a default font
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except IOError:
        font = ImageFont.load_default()

    # Draw text
    text_color = (255, 255, 255)  # White text

    # Get text bounding box
    left, top, right, bottom = d.textbbox((0, 0), initials, font=font)
    text_width = right - left
    text_height = bottom - top

    # Calculate position
    position = (
        (200 - text_width) / 2,
        (200 - text_height) / 2 - top,
    )  # Adjust for the font's baseline
    d.text(position, initials, fill=text_color, font=font)

    # Save image
    filename = f"{username.lower().replace(' ', '_')}_initials.png"
    file_path = os.path.join(app.config["PROFILE_PICS"], filename)
    img.save(file_path)

    return filename


@app.template_filter("profile_pic_url")
def profile_pic_url_filter(user):
    return url_for("static", filename=f"profile_pics/{user.profile_picture}")


@app.context_processor
def inject_user():
    return dict(user=current_user)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            username=form.username.data, email=form.email.data, password=hashed_password
        )

        if form.profile_picture.data:
            file = form.profile_picture.data
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config["PROFILE_PICS"], unique_filename)
            file.save(file_path)
            new_user.profile_picture = unique_filename
        else:
            # Generate initials image
            new_user.profile_picture = generate_initials_image(new_user.username)

        db.session.add(new_user)
        db.session.commit()
        flash("Your account has been created! You are now able to log in", "success")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "error")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))
    else:
        return redirect(url_for("user_dashboard"))


@app.route("/user_dashboard")
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    user_tasks = (
        Task.query.join(Task.assigned_users).filter(User.id == current_user.id).all()
    )
    user_projects = (
        Project.query.join(Task, Project.id == Task.project_id)
        .join(Task.assigned_users)
        .filter(User.id == current_user.id)
        .distinct()
        .all()
    )

    return render_template(
        "user_dashboard.html",
        user=current_user,
        tasks=user_tasks,
        projects=user_projects,
    )


@app.route("/admin_dashboard", methods=["GET", "POST"])
@login_required
@admin_required
def admin_dashboard():

    users = User.query.filter(User.id != current_user.id).all()
    all_projects = Project.query.all()
    all_tasks = Task.query.all()

    for task in all_tasks:
        task.formatted_time_spent = format_time_spent(task.time_spent)

    return render_template(
        "admin_dashboard.html", users=users, projects=all_projects, tasks=all_tasks
    )


pass


@app.route("/user_list", methods=["GET", "POST"])
@login_required
@admin_required
def user_list():

    users = User.query.filter(User.id != current_user.id).all()
    all_projects = Project.query.all()
    all_tasks = Task.query.all()

    return render_template("user_list.html", users=users)


pass


def format_time_spent(hours):
    total_seconds = int(hours * 3600)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@app.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    if request.method == "POST":
        if "add_project" in request.form:
            new_project = Project(
                name=request.form["project_name"],
                description=request.form["project_description"],
                user_id=current_user.id,
            )
            db.session.add(new_project)
            db.session.commit()
            flash("New project added successfully", "success")

    all_projects = Project.query.all()
    all_tasks = Task.query.all()

    return render_template("projects.html", projects=all_projects, tasks=all_tasks)


@app.route("/projects/<int:project_id>/tasks", methods=["GET"])
@login_required
def get_project_tasks(project_id):
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project_id).all()

    task_data = []
    for task in tasks:
        task_info = {
            "title": task.title,
            "status": task.status,
            "due_date": task.due_date.strftime("%Y-%m-%d"),
            "assigned_users": [
                {
                    "username": user.username,
                    "profile_pic_url": url_for(
                        "static", filename=f"profile_pics/{user.profile_picture}"
                    ),
                }
                for user in task.assigned_users
            ],
        }
        task_data.append(task_info)

    return jsonify({"tasks": task_data})


@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if "add_task" in request.form:
        new_task = Task(
            project_id=request.form["project_id"],
            title=request.form["task_title"],
            description=request.form["task_description"],
            status=request.form["task_status"],
            due_date=datetime.strptime(request.form["due_date"], "%Y-%m-%d"),
        )
        db.session.add(new_task)
        db.session.commit()

        assigned_user_ids = request.form.getlist("assigned_to[]")
        for user_id in assigned_user_ids:
            user = User.query.get(user_id)
            if user:
                new_task.assigned_users.append(user)

        if "files[]" in request.files:
            files = request.files.getlist("files[]")
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(file_path)
                    file_type = (
                        "image" if file.content_type.startswith("image") else "document"
                    )
                    new_file = File(
                        task_id=new_task.id,
                        filename=filename,
                        file_path=file_path,
                        file_type=file_type,
                    )
                    db.session.add(new_file)

        db.session.commit()
        flash("New task added successfully", "success")

    users = User.query.filter(User.id != current_user.id).all()
    all_projects = Project.query.all()
    all_tasks = Task.query.all()

    for task in all_tasks:
        task.formatted_time_spent = format_time_spent(task.time_spent)

    return render_template(
        "tasks.html", users=users, projects=all_projects, tasks=all_tasks
    )


@app.route("/track_time", methods=["POST"])
@login_required
def track_time():
    data = request.json  # Get JSON data from the request
    task_id = data.get("task_id")
    time_spent = data.get("time_spent")

    if task_id is None or time_spent is None:
        return (
            jsonify({"success": False, "error": "Missing task_id or time_spent"}),
            400,
        )

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"success": False, "error": "Task not found"}), 404

    task.time_spent += float(time_spent)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/assign_task", methods=["POST"])
@login_required
@admin_required
def assign_task():
    task_id = request.form.get("task_id")
    user_ids = request.form.getlist("user_ids")
    task = Task.query.get_or_404(task_id)

    # Clear current assignments
    task.assigned_users = []

    # Assign new users
    for user_id in user_ids:
        user = User.query.get(user_id)
        if user:
            task.assigned_users.append(user)

    db.session.commit()
    flash("Task assigned successfully", "success")
    return redirect(url_for("admin_dashboard"))


# Password reset functionality
def send_password_reset_email(user):
    token = generate_token(user.email)
    msg = Message("Password Reset Request", recipients=[user.email])
    msg.body = f"""To reset your password, visit the following link:
{url_for('reset_password', token=token, _external=True)}

If you did not make this request, please ignore this email.
"""
    mail.send(msg)


def generate_token(email):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="password-reset-salt")


def verify_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=expiration)
    except:
        return None
    return email


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            try:
                token = generate_token(user.email)
                reset_url = url_for("reset_password", token=token, _external=True)
                send_password_reset_email(user.email, reset_url)
                flash(
                    "Password reset instructions have been sent to your email.", "info"
                )
                return redirect(url_for("login"))
            except Exception as e:
                current_app.logger.error(
                    f"Failed to send password reset email: {str(e)}"
                )
                flash(
                    "An error occurred while sending the password reset email. Please try again later.",
                    "error",
                )
        else:
            flash("No account found with that email address.", "error")
    return render_template("forgot_password.html", form=form)


def send_password_reset_email(email, reset_url):
    msg = Message(
        "Password Reset Request",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[email],
    )
    msg.body = f"""To reset your password, visit the following link:
{reset_url}

If you did not make this request, please ignore this email.
"""
    current_app.logger.info(f"Sending password reset email to {email}")
    mail.send(msg)
    current_app.logger.info(f"Password reset email sent to {email}")


def send_password_reset_email(email, reset_url):
    print(f"Password reset URL for {email}: {reset_url}")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = verify_token(token)
    if not email:
        flash("The password reset link is invalid or has expired.", "error")
        return redirect(url_for("login"))
    user = User.query.filter_by(email=email).first()
    if request.method == "POST":
        password = request.form["password"]
        user.password = generate_password_hash(password)
        db.session.commit()
        flash("Your password has been updated!", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html")


@app.route("/uploads/<filename>")
def serve_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# def uploaded_file(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route("/upload_file/<int:task_id>", methods=["POST"])
@login_required
def upload_file(task_id):
    task = Task.query.get_or_404(task_id)
    if "files[]" not in request.files:
        flash("No file part", "error")
        return redirect(url_for("tasks"))

    files = request.files.getlist("files[]")

    for file in files:
        if file.filename == "":
            continue

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # Determine file type
            mime_type, _ = mimetypes.guess_type(file_path)
            file_type = (
                "image" if mime_type and mime_type.startswith("image") else "document"
            )

            new_file = File(
                task_id=task.id,
                filename=filename,
                file_path=file_path,
                file_type=file_type,
            )
            db.session.add(new_file)
        else:
            flash(f"File {file.filename} is not allowed", "error")

    db.session.commit()
    flash("File(s) uploaded successfully", "success")
    return redirect(url_for("tasks"))


@app.route("/serve_file/<int:file_id>")
@login_required
def serve_file(file_id):
    file = File.query.get_or_404(file_id)
    return send_file(file.file_path)


@app.route("/download_file/<int:file_id>")
@login_required
def download_file(file_id):
    file = MessageFile.query.get_or_404(file_id)
    return send_file(file.file_path, as_attachment=True, download_name=file.filename)


@app.route("/delete_file/<int:file_id>", methods=["POST"])
@login_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    if file:
        try:
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
            db.session.delete(file)
            db.session.commit()
            return jsonify({"success": True, "message": "File deleted successfully"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
    return jsonify({"success": False, "message": "File not found"}), 404


@app.route("/delete_task/<int:task_id>", methods=["POST"])
@login_required
@admin_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted successfully", "success")
    return redirect(url_for("tasks"))


# Update the projects route to include project deletion
@app.route("/delete_project/<int:project_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project_id).all()
    for task in tasks:
        for file in task.files:
            if file.file_path and os.path.exists(file.file_path):
                os.remove(file.file_path)
            db.session.delete(file)
        db.session.delete(task)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/handle_chat_request/<int:request_id>/<string:action>")
@login_required
def handle_chat_request(request_id, action):
    chat_request = ChatRequest.query.get_or_404(request_id)
    if chat_request.receiver_id != current_user.id:
        abort(403)

    if action == "accept":
        chat_request.status = "accepted"
        flash("Chat request accepted", "success")
    elif action == "reject":
        chat_request.status = "rejected"
        flash("Chat request rejected", "info")

    db.session.commit()
    return redirect(url_for("chat_requests"))


@app.route("/chat/<int:user_id>", methods=["GET", "POST"])
@login_required
def chat(user_id):
    other_user = User.query.get_or_404(user_id)
    if other_user not in current_user.friends:
        flash("You can only chat with friends.", "error")
        return redirect(url_for("messages"))

    messages = (
        Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id))
            | (
                (Message.sender_id == user_id)
                & (Message.receiver_id == current_user.id)
            )
        )
        .order_by(Message.timestamp)
        .all()
    )

    if request.method == "POST":
        content = request.form.get("message")
        files = request.files.getlist("files")

        new_message = Message(
            sender_id=current_user.id, receiver_id=user_id, content=content
        )
        db.session.add(new_message)
        db.session.flush()  # This assigns an id to new_message

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add a unique identifier to prevent filename conflicts
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                file.save(file_path)

                file_type = (
                    "image" if file.content_type.startswith("image") else "document"
                )
                new_file = MessageFile(
                    message_id=new_message.id,
                    filename=unique_filename,
                    file_path=file_path,
                    file_type=file_type,
                )
                db.session.add(new_file)

        db.session.commit()
        return redirect(url_for("chat", user_id=user_id))

    return render_template("chat.html", other_user=other_user, messages=messages)


@app.route("/chat_requests")
@login_required
def chat_requests():
    pending_requests = ChatRequest.query.filter_by(
        receiver_id=current_user.id, status="pending", request_type="chat"
    ).all()
    return render_template("chat_requests.html", requests=pending_requests)


@app.route("/send_message/<int:receiver_id>", methods=["POST"])
@login_required
def send_message(receiver_id):
    receiver = User.query.get_or_404(receiver_id)
    if receiver not in current_user.friends:
        flash("You can only send messages to friends.", "error")
        return redirect(url_for("user_profile", user_id=receiver_id))

    content = request.form.get("content")
    if content:
        new_message = Message(
            sender_id=current_user.id, receiver_id=receiver_id, content=content
        )
        db.session.add(new_message)
        db.session.commit()
        flash("Message sent", "success")
    return redirect(url_for("chat", user_id=receiver_id))


@app.route("/send_chat_request/<int:receiver_id>", methods=["POST"])
@login_required
def send_chat_request(receiver_id):
    existing_request = ChatRequest.query.filter_by(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        status="pending",
        request_type="chat",
    ).first()
    if existing_request:
        flash("Chat request already sent", "info")
    else:
        new_request = ChatRequest(
            sender_id=current_user.id, receiver_id=receiver_id, request_type="chat"
        )
        db.session.add(new_request)
        db.session.commit()
        flash("Chat request sent", "success")
    return redirect(url_for("user_profile", user_id=receiver_id))


@app.route("/send_friend_request/<int:receiver_id>", methods=["POST"])
@login_required
def send_friend_request(receiver_id):
    existing_request = ChatRequest.query.filter_by(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        status="pending",
        request_type="friend",
    ).first()
    if existing_request:
        flash("Friend request already sent", "info")
    else:
        new_request = ChatRequest(
            sender_id=current_user.id, receiver_id=receiver_id, request_type="friend"
        )
        db.session.add(new_request)
        db.session.commit()
        flash("Friend request sent", "success")
    return redirect(url_for("user_profile", user_id=receiver_id))


@app.route("/friend_requests")
@login_required
def friend_requests():
    pending_requests = FriendRequest.query.filter_by(
        receiver_id=current_user.id, status="pending"
    ).all()
    return render_template("friend_requests.html", requests=pending_requests)


@app.route("/handle_friend_request/<int:request_id>/<string:action>")
@login_required
def handle_friend_request(request_id, action):
    friend_request = FriendRequest.query.get_or_404(request_id)
    if friend_request.receiver_id != current_user.id:
        abort(403)

    if action == "accept":
        friend_request.status = "accepted"
        current_user.friends.append(friend_request.sender)
        friend_request.sender.friends.append(current_user)
        flash("Friend request accepted", "success")
    elif action == "reject":
        friend_request.status = "rejected"
        flash("Friend request rejected", "info")

    db.session.commit()
    return redirect(url_for("friend_requests"))


# //send_request


@app.route("/send_request/<int:receiver_id>/<string:request_type>", methods=["POST"])
@login_required
def send_request(receiver_id, request_type):
    if request_type not in ["chat", "friend"]:
        abort(400)
    existing_request = ChatRequest.query.filter_by(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        status="pending",
        request_type=request_type,
    ).first()
    if existing_request:
        flash(f"{request_type.capitalize()} request already sent", "info")
    else:
        new_request = ChatRequest(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            request_type=request_type,
        )
        db.session.add(new_request)
        db.session.commit()
        flash(f"{request_type.capitalize()} request sent", "success")
    return redirect(url_for("user_profile", user_id=receiver_id))


# //send_request


# requests
@app.route("/requests")
@login_required
def requests():
    pending_requests = ChatRequest.query.filter_by(
        receiver_id=current_user.id, status="pending"
    ).all()
    return render_template("requests.html", requests=pending_requests)


# requests


@app.route("/handle_request/<int:request_id>/<string:action>")
@login_required
def handle_request(request_id, action):
    chat_request = ChatRequest.query.get_or_404(request_id)
    if chat_request.receiver_id != current_user.id:
        abort(403)

    if action == "accept":
        chat_request.status = "accepted"
        if chat_request.request_type == "friend":
            current_user.friends.append(chat_request.sender)
            chat_request.sender.friends.append(current_user)
        flash(f"{chat_request.request_type.capitalize()} request accepted", "success")
    elif action == "reject":
        chat_request.status = "rejected"
        flash(f"{chat_request.request_type.capitalize()} request rejected", "info")

    db.session.commit()
    return redirect(url_for("messages"))


@app.route("/messages")
@login_required
def messages():
    friends = current_user.friends.all()
    pending_requests = ChatRequest.query.filter_by(
        receiver_id=current_user.id, status="pending"
    ).all()
    return render_template("messages.html", friends=friends, requests=pending_requests)


@app.route("/delete_message/<int:message_id>", methods=["POST"])
@login_required
def delete_message(message_id):
    try:
        message = Message.query.get_or_404(message_id)
        if message.sender_id != current_user.id:
            flash("Unauthorized to delete this message.", "error")
            return redirect(url_for("chat", user_id=message.receiver_id))

        # Delete associated files from the filesystem
        for file in message.files:
            if os.path.exists(file.file_path):
                os.remove(file.file_path)

        other_user_id = (
            message.receiver_id
            if message.sender_id == current_user.id
            else message.sender_id
        )

        db.session.delete(message)
        db.session.commit()

        flash("Message deleted successfully.", "success")

        if request.is_json:
            return jsonify(
                {"success": True, "redirect": url_for("chat", user_id=other_user_id)}
            )
        else:
            return redirect(url_for("chat", user_id=other_user_id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting message: {str(e)}", "error")
        if request.is_json:
            return jsonify({"success": False, "error": str(e)}), 500
        else:
            return redirect(url_for("chat", user_id=other_user_id))


@app.route("/check_message/<int:message_id>", methods=["GET"])
@login_required
def check_message(message_id):
    message = Message.query.get(message_id)
    if message:
        return jsonify({"exists": True, "content": message.content})
    else:
        return jsonify({"exists": False})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin_user()
        print("Database created successfully!")
    app.run(debug=True)

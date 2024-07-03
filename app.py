from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import logging

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)

logging.basicConfig(level=logging.DEBUG)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    projects = db.relationship("Project", backref="user", lazy=True)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tasks = db.relationship("Task", backref="project", lazy=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Not Yet Started")
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


@app.route("/get_projects", methods=["GET"])
def get_projects():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]
    user = User.query.get(user_id)
    projects = [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "description": task.description,
                    "status": task.status,
                }
                for task in project.tasks
            ],
        }
        for project in user.projects
    ]
    logging.debug("Projects fetched: %s", projects)
    return jsonify({"projects": projects})


@app.route("/add_project", methods=["POST"])
def add_project():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]
    name = request.json.get("name")
    description = request.json.get("description")
    new_project = Project(name=name, description=description, user_id=user_id)
    db.session.add(new_project)
    db.session.commit()
    return jsonify(
        {
            "id": new_project.id,
            "name": new_project.name,
            "description": new_project.description,
        },
        201,
    )


@app.route("/add_task", methods=["POST"])
def add_task():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    name = request.json.get("name")
    description = request.json.get("description")
    project_id = request.json.get("project_id")
    new_task = Task(name=name, description=description, project_id=project_id)
    db.session.add(new_task)
    db.session.commit()
    return jsonify(
        {
            "id": new_task.id,
            "name": new_task.name,
            "description": new_task.description,
            "status": new_task.status,
            "project_id": project_id,
        },
        201,
    )


@app.route("/delete_project", methods=["POST"])
def delete_project():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    project_id = request.json.get("project_id")
    project = Project.query.get(project_id)
    if project and project.user_id == session["user_id"]:
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Project not found or unauthorized"}), 404


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

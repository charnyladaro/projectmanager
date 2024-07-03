from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure the SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project_tracker.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database
db = SQLAlchemy(app)


# Define the Project model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200))


# Define the Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200))
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    project = db.relationship("Project", backref=db.backref("tasks", lazy=True))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    projects = Project.query.all()
    return render_template("dashboard.html", projects=projects)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/logout")
def logout():
    return redirect(url_for("index"))


@app.route("/project_tasks/<int:project_id>")
def project_tasks(project_id):
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project_id).all()
    tasks_data = [
        {"id": task.id, "name": task.name, "description": task.description}
        for task in tasks
    ]
    return jsonify({"tasks": tasks_data})


@app.route("/add_project", methods=["POST"])
def add_project():
    data = request.get_json()
    project_name = data["project-name"]
    project_description = data["project-description"]
    new_project = Project(name=project_name, description=project_description)
    db.session.add(new_project)
    db.session.commit()
    return jsonify({"success": True, "project_id": new_project.id})


@app.route("/add_task", methods=["POST"])
def add_task():
    data = request.get_json()
    task_name = data["task-name"]
    task_description = data["task-description"]
    project_id = data["project-id"]
    new_task = Task(name=task_name, description=task_description, project_id=project_id)
    db.session.add(new_task)
    db.session.commit()
    return jsonify({"success": True, "task_id": new_task.id})


@app.route("/delete_project/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": f"Project {project_id} deleted successfully"}), 200


if __name__ == "__main__":
    # Create database and tables
    with app.app_context():
        db.create_all()
    app.run(debug=True)

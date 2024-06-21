from flask import render_template, redirect, url_for, request, jsonify, flash
from . import db
from .models import Project, Task, Comment
from .forms import ProjectForm, TaskForm, CommentForm
from flask import current_app as app
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename
import os


tasks = {
    1: {"id": 1, "name": "Task 1", "status": "Not started"},
    2: {"id": 2, "name": "Task 2", "status": "In progress"},
    3: {"id": 3, "name": "Task 3", "status": "Completed"},
}


@app.route("/")
def index():
    projects = Project.query.all()
    return render_template("index.html", projects=projects)


@app.route("/add_project", methods=["GET", "POST"])
def add_project():
    form = ProjectForm()
    if form.validate_on_submit():
        new_project = Project(name=form.name.data)
        db.session.add(new_project)
        db.session.commit()
        flash("Project added successfully!")
        return redirect(url_for("index"))
    return render_template("add_project.html", form=form)


@app.route("/project/<int:project_id>", methods=["GET", "POST"])
def project(project_id):
    project = Project.query.get_or_404(project_id)
    tasks = project.tasks
    form = TaskForm()
    if form.validate_on_submit():
        new_task = Task(name=form.name.data, project_id=project.id)
        db.session.add(new_task)
        db.session.commit()
        flash("Task added successfully!")
        return redirect(url_for("project", project_id=project_id))
    return render_template("project.html", project=project, tasks=tasks, form=form)


@app.route("/delete_project/<int:project_id>", methods=["POST"])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted successfully!")
    return redirect(url_for("index"))


@app.route("/update_project/<int:project_id>", methods=["POST"])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    new_content = request.form.get("content")

    if new_content:
        project.name = new_content  # Assuming you are updating the project's name
        db.session.commit()
        flash("Project updated successfully!")
    else:
        flash("No content provided for update.")
    return redirect(url_for("index"))


@app.route("/task_detail/<int:task_id>")
def task_detail(task_id):
    task = tasks.get(task_id)
    if task:
        return render_template("task_detail.html", task=task)
    else:
        return jsonify({"error": "Task not found"}), 404


@app.route("/update_task_status/<int:task_id>", methods=["POST"])
def update_task_status(task_id):
    # Example: Updating task status based on POST request data
    new_status = request.json.get("status")  # Assuming status is sent in JSON format
    if new_status:
        tasks[task_id]["status"] = new_status
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "No status provided"}), 400


@app.route("/update_task_name/<int:task_id>", methods=["POST"])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    new_content = request.form.get("content")

    if new_content:
        task.name = new_content
        db.session.commit()
        flash("Task updated successfully!")
    else:
        flash("No content provided for update.")
    return redirect(url_for("index"))


@app.route("/delete_task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted successfully!")
    return redirect(url_for("project", project_id=project_id))


@app.route("/add_comment/<int:task_id>", methods=["POST"])
def add_comment(task_id):
    task = Task.query.get_or_404(task_id)
    content = request.form.get("content")
    new_comment = Comment(content=content, task_id=task_id)
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"success": True, "comment_id": new_comment.id})


@app.route("/update_comment/<int:comment_id>", methods=["POST"])
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    content = request.form.get("content")
    comment.content = content
    db.session.commit()
    return jsonify({"success": True})


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/start_timer/<int:task_id>", methods=["POST"])
def start_timer(task_id):
    task = Task.query.get_or_404(task_id)
    if task.status != "On-going":  # Prevent resetting start time if already running
        task.start_time = datetime.utcnow()
        task.status = "On-going"
        task.timer_status = "On-going"
        task.paused_time = None  # Reset paused time
        db.session.commit()
    return jsonify(success=True)


@app.route("/pause_timer/<int:task_id>", methods=["POST"])
def pause_timer(task_id):
    task = Task.query.get_or_404(task_id)
    if task.status == "On-going":
        task.paused_time = datetime.utcnow()
        task.status = "Paused"
        task.timer_status = "Paused"
        db.session.commit()
    return jsonify(success=True)


@app.route("/stop_timer/<int:task_id>", methods=["POST"])
def stop_timer(task_id):
    task = Task.query.get_or_404(task_id)
    if task.status in ["On-going", "Paused"]:
        task.stop_time = datetime.utcnow()
        task.status = "Done"
        task.timer_status = "Done"
        if task.start_time:
            total_seconds = (task.stop_time - task.start_time).total_seconds()
            if task.paused_time:
                total_seconds -= (task.paused_time - task.start_time).total_seconds()
            task.total_time += total_seconds
        db.session.commit()
    return jsonify(success=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "png",
        "jpg",
        "jpeg",
        "gif",
        "pdf",
        "docx",
    }


@app.route("/upload_file/<int:task_id>", methods=["POST"])
def upload_file(task_id):
    if request.method == "POST":
        task = Task.query.get_or_404(task_id)
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            task.file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            db.session.commit()
            return redirect(url_for("task_detail", task_id=task.id))
        return redirect(request.url)
    else:
        return "Method Not Allowed", 405


@app.template_filter("format_time")
def format_time(seconds):
    duration = timedelta(seconds=seconds)
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02}:{:02}:{:02}".format(hours, minutes, seconds)


app.jinja_env.filters["format_time"] = format_time

if __name__ == "__main__":
    app.run(debug=True)

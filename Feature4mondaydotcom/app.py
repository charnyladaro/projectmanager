from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = "database.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                time_spent INTEGER DEFAULT 0,
                project_id INTEGER,
                file_path TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
            """
        )
        conn.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/add_project", methods=["POST"])
def add_project():
    data = request.json
    project_name = data.get("name")
    if not project_name:
        return jsonify({"success": False, "error": "Project name not provided"}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (name) VALUES (?)", (project_name,))
        conn.commit()

    return jsonify({"success": True})


@app.route("/get_projects")
def get_projects():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM projects")
        projects = [{"id": row["id"], "name": row["name"]} for row in cursor.fetchall()]

    return jsonify({"projects": projects})


@app.route("/get_project_tasks", methods=["GET"])
def get_project_tasks():
    project_id = request.args.get("project_id")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, time_spent, file_path FROM tasks WHERE project_id = ?",
            (project_id,),
        )
        tasks = [
            {
                "id": row["id"],
                "name": row["name"],
                "time_spent": row["time_spent"],
                "file_path": row["file_path"],
            }
            for row in cursor.fetchall()
        ]

    return jsonify({"tasks": tasks})


@app.route("/add_task_to_project", methods=["POST"])
def add_task_to_project():
    task_name = request.form.get("name")
    project_id = request.form.get("project_id")

    # Check if file is included in the request
    if "file" in request.files:
        file = request.files["file"]
        # Save the file to a desired location
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)
    else:
        file_path = None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (name, project_id, file_path) VALUES (?, ?, ?)",
            (task_name, project_id, file_path),
        )
        conn.commit()

    return jsonify({"success": True})


@app.route("/upload_file_to_project", methods=["POST"])
def upload_file_to_project():
    if request.method == "POST":
        file = request.files["file"]
        project_id = request.form.get("project_id")
        if file and project_id:
            filename = file.filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO files (filename, project_id) VALUES (?, ?)",
                    (filename, project_id),
                )
                conn.commit()

            return (
                jsonify(
                    {"success": True, "filename": filename, "project_id": project_id}
                ),
                201,
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "File and project ID are required"}
                ),
                400,
            )
    else:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects")
            projects = cursor.fetchall()
        projects_list = [
            {"id": project["id"], "name": project["name"]} for project in projects
        ]
        return jsonify({"projects": projects_list})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/download_file/<task_id>", methods=["GET"])
def download_file(task_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row and row["file_path"]:
            file_path = row["file_path"]
            return send_from_directory(
                directory=os.path.dirname(file_path),
                path=os.path.basename(file_path),
                as_attachment=True,
            )
    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/update_task_time", methods=["POST"])
def update_task_time():
    data = request.json
    task_id = data.get("id")
    time_spent = data.get("time_spent")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET time_spent = ? WHERE id = ?", (time_spent, task_id)
        )
        conn.commit()

    return jsonify({"success": True})


@app.route("/delete_project", methods=["POST"])
def delete_project():
    data = request.json
    project_id = data.get("id")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        cursor.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        conn.commit()

    return jsonify({"success": True})


@app.route("/delete_task", methods=["POST"])
def delete_task():
    data = request.json
    task_id = data.get("id")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()

    return jsonify({"success": True})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

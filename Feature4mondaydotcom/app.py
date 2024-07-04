from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

DATABASE = "database.db"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


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
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            time_spent INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
        """
        )

        conn.commit()


# Call init_db to initialize the database
init_db()


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


@app.route("/get_projects", methods=["GET"])
def get_projects():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects")
        projects = cursor.fetchall()

    return jsonify({"projects": [dict(row) for row in projects]})


@app.route("/get_project_tasks", methods=["GET"])
def get_project_tasks():
    project_id = request.args.get("project_id")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,))
        tasks = cursor.fetchall()

        task_list = []
        for task in tasks:
            task_dict = dict(task)
            cursor.execute("SELECT * FROM files WHERE task_id = ?", (task["id"],))
            files = cursor.fetchall()
            task_dict["files"] = [dict(file) for file in files]
            task_list.append(task_dict)

    return jsonify({"tasks": task_list})


@app.route("/add_task_to_project", methods=["POST"])
def add_task_to_project():
    data = request.get_json()
    name = data.get("name")
    project_id = data.get("project_id")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (name, project_id) VALUES (?, ?)", (name, project_id)
        )
        conn.commit()

    return jsonify({"success": True})


# Updated function to handle file uploads
@app.route("/upload_file_to_project", methods=["POST"])
def upload_file_to_project():
    project_id = request.form.get("project_id")
    file = request.files.get("file")

    if not project_id or not file:
        return (
            jsonify({"success": False, "error": "Project ID or file not provided"}),
            400,
        )

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM tasks WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        )
        task = cursor.fetchone()

        if task:
            cursor.execute(
                "INSERT INTO files (file_path, task_id) VALUES (?, ?)",
                (filename, task["id"]),
            )
            conn.commit()

    return jsonify({"success": True})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/upload_file", methods=["POST"])
def upload_file():
    project_id = request.form["project_id"]
    task_id = request.form["task_id"]
    file = request.files["file"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND id = ?", (project_id, task_id)
        )
        task = cursor.fetchone()

        if not task:
            return jsonify(
                {
                    "success": False,
                    "message": "No task found. You must add a task before uploading files.",
                }
            )

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        cursor.execute(
            "INSERT INTO files (task_id, file_path) VALUES (?, ?)",
            (task_id, file.filename),
        )
        conn.commit()

    return jsonify({"success": True})


@app.route("/delete_project", methods=["POST"])
def delete_project():
    project_id = request.json["id"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,))
        tasks = cursor.fetchall()

        if tasks:
            return jsonify(
                {
                    "success": False,
                    "message": "Cannot delete project with existing tasks.",
                }
            )

        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()

    return jsonify({"success": True})


@app.route("/delete_task", methods=["POST"])
def delete_task():
    task_data = request.json
    task_id = task_data["id"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as file_count FROM files WHERE task_id = ?", (task_id,)
        )
        result = cursor.fetchone()

        if result["file_count"] > 0:
            return jsonify(
                {"success": False, "message": "Cannot delete task with uploaded files."}
            )

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()

    return jsonify({"success": True})


@app.route("/delete_file", methods=["POST"])
def delete_file():
    file_data = request.json
    file_id = file_data["id"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM files WHERE id = ?", (file_id,))
        file = cursor.fetchone()

        if not file:
            return jsonify({"success": False, "message": "File not found."})

        file_path = file["file_path"]

        try:
            os.remove(os.path.join("uploads", file_path))
        except FileNotFoundError:
            pass  # File already deleted from filesystem, but not from DB

        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()

    return jsonify({"success": True})


@app.route("/update_task_time", methods=["POST"])
def update_task_time():
    data = request.get_json()
    task_id = data.get("id")
    time_spent = data.get("time_spent")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET time_spent = ? WHERE id = ?", (time_spent, task_id)
        )
        conn.commit()

    return jsonify({"success": True})


if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(debug=True)

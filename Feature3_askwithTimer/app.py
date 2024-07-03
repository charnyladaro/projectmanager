from flask import Flask, render_template, request, redirect, jsonify, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = "database.db"


def adapt_datetime(ts):
    return ts.isoformat()


def convert_datetime(ts):
    return datetime.fromisoformat(ts.decode("utf-8"))


# Register the adapter and converter
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)


def init_db():
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT NOT NULL, 
                  description TEXT, 
                  due_date TEXT, 
                  completed BOOLEAN NOT NULL CHECK (completed IN (0, 1)),
                  time_spent INTEGER DEFAULT 0,
                  timer_start DATETIME,
                  hold_start DATETIME,
                  hold_time REAL DEFAULT 0)"""
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("SELECT * FROM tasks")
    tasks = c.fetchall()
    conn.close()
    return render_template("index.html", tasks=tasks)


@app.route("/add_task", methods=["POST"])
def add_task():
    title = request.form["title"]
    description = request.form.get("description", "")
    due_date = request.form.get("due_date", "")
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title, description, due_date, completed) VALUES (?, ?, ?, ?)",
        (title, description, due_date, False),
    )
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed = ? WHERE id = ?", (True, task_id))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/start_timer/<int:task_id>", methods=["POST"])
def start_timer(task_id):
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    with conn:  # This will automatically commit or rollback transactions
        c = conn.cursor()
        c.execute(
            "UPDATE tasks SET timer_start = ? WHERE id = ?",
            (datetime.now(), task_id),
        )
    return jsonify(status="timer started")


@app.route("/stop_timer/<int:task_id>", methods=["POST"])
def stop_timer(task_id):
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # Ensure row factory to return sqlite3.Row
    datenow = datetime.now()
    c = conn.cursor()
    c.execute("SELECT timer_start, time_spent FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    if row and row["timer_start"]:
        timer_start = (
            datetime.fromisoformat(row["timer_start"])
            if isinstance(row["timer_start"], str)
            else row["timer_start"]
        )
        time_spent = row["time_spent"] + (datenow - timer_start).total_seconds()
        c.execute(
            "UPDATE tasks SET timer_start = NULL, time_spent = ? WHERE id = ?",
            (time_spent, task_id),
        )
    conn.commit()
    conn.close()
    return jsonify(status="timer stopped")


@app.route("/hold_timer/<int:task_id>", methods=["POST"])
def hold_timer(task_id):
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # Ensure row factory to return sqlite3.Row
    datenow = datetime.now()
    c = conn.cursor()
    c.execute("SELECT timer_start, hold_time FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    if row and row["timer_start"]:
        timer_start = (
            datetime.fromisoformat(row["timer_start"])
            if isinstance(row["timer_start"], str)
            else row["timer_start"]
        )
        hold_time = row["hold_time"] + (datenow - timer_start).total_seconds()
        c.execute(
            "UPDATE tasks SET timer_start = NULL, hold_time = ?, hold_start = ? WHERE id = ?",
            (hold_time, datenow, task_id),
        )
        conn.commit()
        conn.close()
        return jsonify(status="timer held")
    else:
        conn.close()
        return jsonify(status="task not found or timer not started"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

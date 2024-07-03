from datetime import datetime
from . import db  # Assuming you have initialized 'db' as SQLAlchemy instance


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tasks = db.relationship("Task", backref="project", lazy=True)

    def __repr__(self):
        return f"Project('{self.name}')"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=True)
    stop_time = db.Column(db.DateTime, nullable=True)
    paused_time = db.Column(db.DateTime, nullable=True)
    total_time = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="Not-yet-started")
    file_path = db.Column(db.String(200), nullable=True)  # New column for file path
    comments = db.relationship("Comment", backref="task", lazy=True)

    def start_timer(self):
        if self.status != "On-going":
            if self.paused_time:
                pause_duration = (
                    datetime.datetime.utcnow() - self.paused_time
                ).total_seconds()
                self.start_time = self.start_time + datetime.timedelta(
                    seconds=pause_duration
                )
                self.paused_time = None
            else:
                self.start_time = datetime.datetime.utcnow()
            self.status = "On-going"

    def pause_timer(self):
        if self.status == "On-going":
            self.paused_time = datetime.datetime.utcnow()
            if self.start_time:
                elapsed = (self.paused_time - self.start_time).total_seconds()
                self.total_time += elapsed
            self.status = "Paused"

    def stop_timer(self):
        if self.status in ["On-going", "Paused"]:
            self.stop_time = datetime.datetime.utcnow()
            if self.status == "On-going":
                elapsed = (self.stop_time - self.start_time).total_seconds()
                self.total_time += elapsed
            self.start_time = None
            self.paused_time = None
            self.status = "Done"

    def __repr__(self):
        return f"Task('{self.name}', '{self.status}', '{self.total_time}')"


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)

    def __repr__(self):
        return f"Comment('{self.content}')"

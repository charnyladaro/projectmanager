from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired


class ProjectForm(FlaskForm):
    name = StringField("Project Name", validators=[DataRequired()])
    submit = SubmitField("Add Project")


class TaskForm(FlaskForm):
    name = StringField("Task Name", validators=[DataRequired()])
    submit = SubmitField("Add Task")


class CommentForm(FlaskForm):
    content = TextAreaField("Comment", validators=[DataRequired()])
    submit = SubmitField("Add Comment")

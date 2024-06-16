# app.py
from flask import Flask, request, jsonify
from config import Config
from models import db, Project, Task

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

@app.route('/projects', methods=['GET', 'POST'])
def handle_projects():
    if request.method == 'POST':
        data = request.json
        new_project = Project(name=data['name'], description=data['description'])
        db.session.add(new_project)
        db.session.commit()
        return jsonify({'id': new_project.id}), 201
    elif request.method == 'GET':
        projects = Project.query.all()
        return jsonify([{'id': project.id, 'name': project.name, 'description': project.description} for project in projects])

@app.route('/tasks', methods=['POST'])
def handle_tasks():
    data = request.json
    new_task = Task(name=data['name'], description=data['description'], project_id=data['project_id'])
    db.session.add(new_task)
    db.session.commit()
    return jsonify({'id': new_task.id}), 201

@app.route('/projects/<int:project_id>/tasks', methods=['GET'])
def get_tasks(project_id):
    tasks = Task.query.filter_by(project_id=project_id).all()
    return jsonify([{'id': task.id, 'name': task.name, 'description': task.description} for task in tasks])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, send_from_directory,abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import mimetypes
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from sqlalchemy.orm import relationship
from email_validator import validate_email, EmailNotValidError


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'project_management.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'capstone'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Change this to your email server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Change this to your email
app.config['MAIL_PASSWORD'] = 'your-email-password'  # Change this to your email password
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'  # Change this to your email
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
csrf = CSRFProtect(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)
csrf.init_app(app)

# Models

task_assignments = db.Table('task_assignments',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    assigned_tasks = relationship('Task', secondary=task_assignments, back_populates='assigned_users')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='To Do')
    due_date = db.Column(db.DateTime)
    time_spent = db.Column(db.Float, default=0)
    files = relationship('File', back_populates='task', lazy=True, cascade="all, delete-orphan")
    assigned_users = relationship('User', secondary=task_assignments, back_populates='assigned_tasks')

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'image' or 'document'
    task = relationship('Task', back_populates='files') 

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        try:
            valid = validate_email(email.data)
            email.data = valid.email
        except EmailNotValidError as e:
            raise ValidationError(str(e))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/get-csrf-token', methods=['GET'])
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

# Define allowed extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

def create_admin_user():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.password = generate_password_hash('adminpassword')
        db.session.add(admin)
        print("Admin user created")
    else:
        admin.email = 'admin@example.com'  # Update email if needed
        admin.is_admin = True  # Ensure admin status
        admin.password = generate_password_hash('adminpassword')  # Update password
        print("Admin user updated")
    
    db.session.commit()

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    user_tasks = Task.query.join(Task.assigned_users).filter(User.id == current_user.id).all()
    user_projects = Project.query.join(Task, Project.id == Task.project_id).join(Task.assigned_users).filter(User.id == current_user.id).distinct().all()

    return render_template('user_dashboard.html',
                           user=current_user,
                           tasks=user_tasks,
                           projects=user_projects)

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_dashboard():
    if request.method == 'POST':
        if 'add_project' in request.form:
            new_project = Project(
                name=request.form['project_name'],
                description=request.form['project_description'],
                user_id=current_user.id
            )
            db.session.add(new_project)
            db.session.commit()
            flash('New project added successfully', 'success')
        elif 'add_task' in request.form:
            new_task = Task(
                project_id=request.form['project_id'],
                title=request.form['task_title'],
                description=request.form['task_description'],
                status=request.form['task_status'],
                due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d')
            )
            db.session.add(new_task)
            db.session.commit()

            assigned_user_ids = request.form.getlist('assigned_to')
            for user_id in assigned_user_ids:
                user = User.query.get(user_id)
                if user:
                    new_task.assigned_users.append(user)

            if 'files[]' in request.files:
                files = request.files.getlist('files[]')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)                        
                        file_type = 'image' if file.content_type.startswith('image') else 'document'
                        new_file = File(task_id=new_task.id, filename=filename, file_path=file_path, file_type=file_type)
                        db.session.add(new_file)
            
            db.session.commit()
            flash('New task added successfully', 'success')

    users = User.query.filter(User.id != current_user.id).all()
    all_projects = Project.query.all()
    all_tasks = Task.query.all()

    for task in all_tasks:
        task.formatted_time_spent = format_time_spent(task.time_spent)

    return render_template('admin_dashboard.html',
                           users=users,
                           projects=all_projects,
                           tasks=all_tasks)


def format_time_spent(hours):
    total_seconds = int(hours * 3600)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@app.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    if request.method == 'POST':
        new_project = Project(name=request.form['name'], description=request.form['description'], user_id=current_user.id)
        db.session.add(new_project)
        db.session.commit()
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('projects.html', projects=projects)

@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    if request.method == 'POST':
        new_task = Task(
            project_id=request.form['project_id'],
            title=request.form['title'],
            description=request.form['description'],
            status=request.form['status'],
            assigned_to=request.form['assigned_to'],
            due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        )
        db.session.add(new_task)
        db.session.commit()
    tasks = Task.query.join(Project).filter(Project.user_id == current_user.id).all()
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('tasks.html', tasks=tasks, projects=projects)

@app.route('/track_time', methods=['POST'])
@login_required
def track_time():
    data = request.json  # Get JSON data from the request
    task_id = data.get('task_id')
    time_spent = data.get('time_spent')
    
    if task_id is None or time_spent is None:
        return jsonify({'success': False, 'error': 'Missing task_id or time_spent'}), 400
    
    task = Task.query.get(task_id)
    if task is None:
        return jsonify({'success': False, 'error': 'Task not found'}), 404
    
    task.time_spent += float(time_spent)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/assign_task', methods=['POST'])
@login_required
@admin_required
def assign_task():
    task_id = request.form.get('task_id')
    user_ids = request.form.getlist('user_ids')
    task = Task.query.get_or_404(task_id)
    
    # Clear current assignments
    task.assigned_users = []
    
    # Assign new users
    for user_id in user_ids:
        user = User.query.get(user_id)
        if user:
            task.assigned_users.append(user)
    
    db.session.commit()
    flash('Task assigned successfully', 'success')
    return redirect(url_for('admin_dashboard'))

# Password reset functionality
def send_password_reset_email(user):
    token = generate_token(user.email)
    msg = Message('Password Reset Request',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_password', token=token, _external=True)}

If you did not make this request, please ignore this email.
'''
    mail.send(msg)

def generate_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')

def verify_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return None
    return email

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_password_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'info')
        else:
            flash('Email address not found', 'error')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_token(token)
    if not email:
        flash('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=email).first()
    if request.method == 'POST':
        password = request.form['password']
        user.password = generate_password_hash(password)
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/upload_file/<int:task_id>', methods=['POST'])
@login_required
def upload_file(task_id):
    task = Task.query.get_or_404(task_id)
    if 'files[]' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('tasks'))
    
    files = request.files.getlist('files[]')
    
    for file in files:
        if file.filename == '':
            continue
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Determine file type
            mime_type, _ = mimetypes.guess_type(file_path)
            file_type = 'image' if mime_type and mime_type.startswith('image') else 'document'
            
            new_file = File(task_id=task.id, filename=filename, file_path=file_path, file_type=file_type)
            db.session.add(new_file)
    
    db.session.commit()
    flash('File(s) uploaded successfully', 'success')
    return redirect(url_for('tasks'))


@app.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    return send_file(file.file_path, as_attachment=True, download_name=file.filename)

@app.route('/serve_file/<int:file_id>')
@login_required
def serve_file(file_id):
    file = File.query.get_or_404(file_id)
    return send_from_directory(os.path.dirname(file.file_path), os.path.basename(file.file_path))

@app.route('/delete_file/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    if file:
        os.remove(file.file_path)
        db.session.delete(file)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/delete_task/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.file_path:
        os.remove(task.file_path)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})

# Update the projects route to include project deletion
@app.route('/delete_project/<int:project_id>', methods=['DELETE'])
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
    return jsonify({'success': True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
        print("Database created successfully!")
    app.run(debug=True)
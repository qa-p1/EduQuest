from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, db
import os
from dotenv import load_dotenv
import json
import bcrypt
import re
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

try:
    firebase_admin.get_app()
except ValueError:
    service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')

    if service_account_json:
        try:
            service_account_info = json.loads(service_account_json)
            firebase_credentials = credentials.Certificate(service_account_info)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from environment variable: {e}")
            raise

    firebase_admin.initialize_app(firebase_credentials, {
        'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
    })

database = db.reference('/')


# Function to get menu items based on user type
def get_menu_items(user_type):
    menu_items = []

    # Base directory for templates
    base_dir = os.path.join(app.root_path, 'templates')

    # Check if user type directory exists
    user_type_dir = os.path.join(base_dir, user_type)
    if os.path.isdir(user_type_dir):
        # Get all HTML files in the user type directory
        files = [f for f in os.listdir(user_type_dir) if f.endswith('.html')]

        for file in files:
            # Remove .html extension
            name = os.path.splitext(file)[0]

            # Skip certain files that shouldn't be in menu
            if name in ['base', 'layout', 'components']:
                continue

            # Format the display name (capitalize, replace underscores with spaces)
            display_name = name.replace('_', ' ').title()

            # Get route function name (convert to snake_case if needed)
            route_name = f"{user_type}_{name}" if name != 'dashboard' else f"{user_type}_dashboard"

            # Create icon mapping based on common naming patterns
            icon_mapping = {
                'dashboard': 'fas fa-home',
                'profile': 'fas fa-user',
                'students': 'fas fa-users',
                'manage_students': 'fas fa-users',
                'exams': 'fas fa-file-alt',
                'generate_exam': 'fas fa-file-alt',
                'submissions': 'fas fa-clipboard-check',
                'quiz': 'fas fa-question-circle',
                'results': 'fas fa-chart-bar',
                'settings': 'fas fa-cog',
                'subjects': 'fas fa-book',
                'add_subject': 'fas fa-book',
                'add_question': 'fas fa-plus-circle',
                'teachers': 'fas fa-chalkboard-teacher'
            }

            # Default icon if not found in mapping
            icon = icon_mapping.get(name, 'fas fa-circle')

            menu_items.append({
                'name': display_name,
                'route': route_name,
                'icon': icon
            })

    # Add common menu items
    menu_items.append({
        'name': 'Profile',
        'route': 'profile',
        'icon': 'fas fa-user'
    })

    return menu_items


def login_required(user_types=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in to access this page")
                return redirect(url_for('login'))

            if user_types and session.get('user_type') not in user_types:
                flash(f"You don't have permission to access this page")
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None


# Function to hash password
def hash_password(password):
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')  # Store as string in the database


# Function to check password
def check_password(stored_hash, provided_password):
    # Check if the provided password matches the stored hash
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required()
def dashboard():
    user_type = session.get('user_type')

    if user_type == 'student':
        return redirect(url_for('student_dashboard'))
    elif user_type == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif user_type == 'admin':
        return redirect(url_for('admin_dashboard'))

    # If user_type is not set properly, log them out
    session.clear()
    flash("Session error. Please log in again.")
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    user_type = request.args.get('user_type') or request.form.get('user_type')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Validate email format
        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return render_template('login.html', user_type=user_type)

        try:
            # Sanitize email for use as Firebase key
            firebase_email_key = email.replace('.', ',')

            if user_type == 'admin':
                # Check admin credentials
                admin_ref = database.child(f'administrators/admins/{firebase_email_key}')
                admin_data = admin_ref.get()

                if admin_data and check_password(admin_data.get("password"), password):
                    session['user_id'] = firebase_email_key
                    session['email'] = email
                    session['user_type'] = 'admin'
                    session['name'] = admin_data.get("name", "Admin")
                    return redirect(url_for('dashboard'))

            elif user_type == 'teacher':
                # Check teacher credentials
                teacher_ref = database.child(f'administrators/teachers/{firebase_email_key}')
                teacher_data = teacher_ref.get()

                if teacher_data and check_password(teacher_data.get("password"), password):
                    session['user_id'] = firebase_email_key
                    session['email'] = email
                    session['user_type'] = 'teacher'
                    session['name'] = teacher_data.get("name", "Teacher")
                    return redirect(url_for('dashboard'))

            elif user_type == 'student':
                # Check student credentials
                student_ref = database.child(f'students/{firebase_email_key}')
                student_data = student_ref.get()

                if student_data and check_password(student_data.get("password"), password):
                    session['user_id'] = firebase_email_key
                    session['email'] = email
                    session['user_type'] = 'student'
                    session['name'] = student_data.get("name", "Student")
                    session['active'] = student_data.get("active", False)
                    return redirect(url_for('dashboard'))

            flash("Invalid credentials. Please try again.")
        except Exception as e:
            flash(f"Authentication error: {str(e)}")
            print(f"Login error: {str(e)}")

    return render_template('login.html', user_type=user_type)


@app.route('/quiz')
def quiz():
    # Get subjects from Firebase for dropdown
    subjects = []
    try:
        subjects_ref = database.child('subjects')
        subjects_data = subjects_ref.get()
        if subjects_data:
            for key, value in subjects_data.items():
                subjects.append({"id": key, "name": value.get("name", "Unknown")})
    except Exception as e:
        print(f"Error fetching subjects: {e}")

    return render_template('student/quiz.html', subjects=subjects)


@app.route('/admin')
def admin():
    user_type = request.args.get('user_type', 'admin')
    return redirect(url_for('login', user_type=user_type))


@app.route('/add_subject', methods=['GET', 'POST'])
@login_required(user_types=['admin'])
def add_subject():
    subjects = []

    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        if subject_name:
            try:
                # Add new subject to Firebase
                subjects_ref = database.child('subjects')
                new_subject_ref = subjects_ref.push()
                new_subject_ref.set({"name": subject_name})
                flash(f"Subject '{subject_name}' added successfully!")
            except Exception as e:
                flash(f"Error adding subject: {e}")

    # Get current subjects
    try:
        subjects_ref = database.child('subjects')
        subjects_data = subjects_ref.get()
        if subjects_data:
            for key, value in subjects_data.items():
                subjects.append({"id": key, "name": value.get("name", "Unknown")})
    except Exception as e:
        flash(f"Error fetching subjects: {e}")

    # Get menu items
    menu_items = get_menu_items(session.get('user_type', 'admin'))
    return render_template('add_subject.html', subjects=subjects, menu_items=menu_items)


@app.route('/student/dashboard')
@login_required(user_types=['student'])
def student_dashboard():
    # Get menu items
    menu_items = get_menu_items('student')
    return render_template('student/dashboard.html', menu_items=menu_items)


# teacher part
@app.route('/teacher/dashboard')
@login_required(user_types=['teacher'])
def teacher_dashboard():
    # Get menu items
    menu_items = get_menu_items('teacher')
    return render_template('teacher/dashboard.html', menu_items=menu_items)


@app.route('/teacher/generate_exam')
@login_required(user_types=['teacher'])
def generate_exam():
    # Get menu items
    menu_items = get_menu_items('teacher')
    return render_template('teacher/generate_exam.html', menu_items=menu_items)


@app.route('/teacher/submissions')
@login_required(user_types=['teacher'])
def submissions():
    # Get menu items
    menu_items = get_menu_items('teacher')
    return render_template('teacher/submissions.html', menu_items=menu_items)


@app.route('/teacher/manage_students')
@login_required(user_types=['teacher'])
def manage_students():
    # Get menu items
    menu_items = get_menu_items('teacher')
    return render_template('teacher/manage_students.html', menu_items=menu_items)


@app.route('/admin/dashboard')
@login_required(user_types=['admin'])
def admin_dashboard():
    # Get menu items
    menu_items = get_menu_items('admin')
    return render_template('admin/dashboard.html', menu_items=menu_items)


@app.route('/profile')
@login_required()
def profile():
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    # Get menu items
    menu_items = get_menu_items(user_type)

    try:
        if user_type == 'student':
            user_ref = database.child(f'students/{user_id}')
        elif user_type == 'teacher':
            user_ref = database.child(f'administrators/teachers/{user_id}')
        elif user_type == 'admin':
            user_ref = database.child(f'administrators/admins/{user_id}')
        else:
            flash("Invalid user type.")
            return redirect(url_for('logout'))

        user_data = user_ref.get()
        return render_template('profile.html', user_data=user_data, menu_items=menu_items)

    except Exception as e:
        flash(f"Error loading profile: {str(e)}")
        return redirect(url_for('dashboard'))


@app.route('/delete_subject/<subject_id>')
@login_required(user_types=['admin'])
def delete_subject(subject_id):
    if not session.get('admin'):
        flash("You must be logged in to access admin panel.")
        return redirect(url_for('admin'))

    try:
        subject_ref = database.child(f'subjects/{subject_id}')
        subject_ref.delete()
        flash("Subject deleted successfully!")
    except Exception as e:
        flash(f"Error deleting subject: {e}")

    return redirect(url_for('add_subject'))


@app.route('/update_subject/<subject_id>', methods=['POST'])
@login_required(user_types=['admin'])
def update_subject(subject_id):
    if not session.get('admin'):
        flash("You must be logged in to access admin panel.")
        return redirect(url_for('admin'))

    new_name = request.form.get('new_name')
    if new_name:
        try:
            subject_ref = database.child(f'subjects/{subject_id}')
            subject_ref.update({"name": new_name})
            flash("Subject updated successfully!")
        except Exception as e:
            flash(f"Error updating subject: {e}")

    return redirect(url_for('add_subject'))


def teacher_teaches_subject(teacher_id, subject_id):
    try:
        teacher_ref = database.child(f'administrators/teachers/{teacher_id}')
        teacher_data = teacher_ref.get()

        if not teacher_data or 'subjects' not in teacher_data:
            return False

        # Get subject name from subject_id
        subject_ref = database.child(f'subjects/{subject_id}')
        subject_data = subject_ref.get()

        if not subject_data or 'name' not in subject_data:
            return False

        subject_name = subject_data.get('name').lower()

        # Check if the teacher teaches this subject
        teacher_subjects = [s.lower() for s in teacher_data.get('subjects', [])]
        return subject_name in teacher_subjects

    except Exception as e:
        print(f"Error checking teacher subjects: {e}")
        return False


# Update the add_question route to handle teacher access
@app.route('/add_question', methods=['GET', 'POST'])
@login_required(user_types=['admin', 'teacher'])  # Allow both admin and teacher
def add_question():
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    # Get menu items
    menu_items = get_menu_items(user_type)

    # Get subjects for dropdown
    subjects = []
    try:
        subjects_ref = database.child('subjects')
        subjects_data = subjects_ref.get()
        if subjects_data:
            for key, value in subjects_data.items():
                # For teachers, only show subjects they teach
                if user_type == 'teacher':
                    if teacher_teaches_subject(user_id, key):
                        subjects.append({"id": key, "name": value.get("name", "Unknown")})
                else:  # Admin sees all subjects
                    subjects.append({"id": key, "name": value.get("name", "Unknown")})
    except Exception as e:
        flash(f"Error fetching subjects: {e}")

        # If teacher has no subjects to teach, show message
    if user_type == 'teacher' and not subjects:
        flash("You don't have any assigned subjects to add questions for. Please contact an administrator.")
        return redirect(url_for('teacher_dashboard'))

        # Get teacher's questions
    teacher_questions = []
    subject_names = {subject["id"]: subject["name"] for subject in subjects}

    if user_type == 'teacher':
        try:
            questions_ref = database.child('questions')
            all_questions = questions_ref.get()
            if all_questions:
                for q_id, q_data in all_questions.items():
                    if q_data.get('created_by') == user_id:
                        subject_id = q_data.get('subject_id')
                        teacher_questions.append({
                            'id': q_id,
                            'text': q_data.get('text', ''),
                            'subject_id': subject_id,
                            'subject_name': subject_names.get(subject_id, 'Unknown Subject'),
                            'difficulty': q_data.get('difficulty', 'medium'),
                            'created_at': q_data.get('created_at', '')
                        })
        except Exception as e:
            flash(f"Error fetching questions: {e}")

    if request.method == 'POST':
        subject_id = request.form.get('subject')
        question_text = request.form.get('question_text')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_answer = request.form.get('correct_answer')
        difficulty = request.form.get('difficulty')

        # Validate required fields
        if not all([subject_id, question_text, option1, option2, option3, option4, correct_answer, difficulty]):
            flash("All fields are required.")
            return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                   menu_items=menu_items)

        # For teachers, verify they can add questions for this subject
        if user_type == 'teacher' and not teacher_teaches_subject(user_id, subject_id):
            flash("You are not authorized to add questions for this subject.")
            return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                   menu_items=menu_items)

        # Create question data
        question_data = {
            "subject_id": subject_id,
            "text": question_text,
            "options": {
                "1": option1,
                "2": option2,
                "3": option3,
                "4": option4
            },
            "correct_answer": correct_answer,
            "difficulty": difficulty,
            "created_by": user_id,
            "created_by_type": user_type,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            # Add question to Firebase
            questions_ref = database.child('questions')
            new_question_ref = questions_ref.push()
            new_question_ref.set(question_data)
            flash("Question added successfully!")
            # Clear form by redirecting
            return redirect(url_for('add_question'))
        except Exception as e:
            flash(f"Error adding question: {e}")

    return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                           menu_items=menu_items)


@app.route('/edit_question/<question_id>', methods=['GET', 'POST'])
@login_required(user_types=['admin', 'teacher'])
def edit_question(question_id):
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    # Get menu items
    menu_items = get_menu_items(user_type)

    # Get question data
    try:
        question_ref = database.child(f'questions/{question_id}')
        question_data = question_ref.get()

        if not question_data:
            flash("Question not found.")
            return redirect(url_for('add_question'))

        # Verify ownership
        if user_type == 'teacher' and question_data.get('created_by') != user_id:
            flash("You do not have permission to edit this question.")
            return redirect(url_for('add_question'))

        # Get subjects for dropdown
        subjects = []
        try:
            subjects_ref = database.child('subjects')
            subjects_data = subjects_ref.get()
            if subjects_data:
                for key, value in subjects_data.items():
                    # For teachers, only show subjects they teach
                    if user_type == 'teacher':
                        if teacher_teaches_subject(user_id, key):
                            subjects.append({"id": key, "name": value.get("name", "Unknown")})
                    else:  # Admin sees all subjects
                        subjects.append({"id": key, "name": value.get("name", "Unknown")})
        except Exception as e:
            flash(f"Error fetching subjects: {e}")

        if request.method == 'POST':
            subject_id = request.form.get('subject')
            question_text = request.form.get('question_text')
            option1 = request.form.get('option1')
            option2 = request.form.get('option2')
            option3 = request.form.get('option3')
            option4 = request.form.get('option4')
            correct_answer = request.form.get('correct_answer')
            difficulty = request.form.get('difficulty')

            # Validate required fields
            if not all([subject_id, question_text, option1, option2, option3, option4, correct_answer, difficulty]):
                flash("All fields are required.")
                return render_template('edit_question.html', question=question_data, question_id=question_id,
                                       subjects=subjects, menu_items=menu_items)

            # Update question data
            updated_data = {
                "subject_id": subject_id,
                "text": question_text,
                "options": {
                    "1": option1,
                    "2": option2,
                    "3": option3,
                    "4": option4
                },
                "correct_answer": correct_answer,
                "difficulty": difficulty,
                "updated_by": user_id,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            try:
                question_ref.update(updated_data)
                flash("Question updated successfully!")
                return redirect(url_for('add_question'))
            except Exception as e:
                flash(f"Error updating question: {e}")

        return render_template('edit_question.html', question=question_data, question_id=question_id, subjects=subjects,
                               menu_items=menu_items)

    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for('add_question'))


@app.route('/delete_question/<question_id>')
@login_required(user_types=['admin', 'teacher'])
def delete_question(question_id):
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    try:
        # Get question data first to verify ownership
        question_ref = database.child(f'questions/{question_id}')
        question_data = question_ref.get()

        if not question_data:
            flash("Question not found.")
            return redirect(url_for('add_question'))

        # Verify ownership for teachers
        if user_type == 'teacher' and question_data.get('created_by') != user_id:
            flash("You do not have permission to delete this question.")
            return redirect(url_for('add_question'))

        # Delete the question
        question_ref.delete()
        flash("Question deleted successfully!")
    except Exception as e:
        flash(f"Error deleting question: {e}")

    return redirect(url_for('add_question'))


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for('index'))


# Context processor to make menu_items available to all templates
@app.context_processor
def inject_menu_items():
    if 'user_type' in session:
        return {'menu_items': get_menu_items(session.get('user_type'))}
    return {'menu_items': []}


if __name__ == '__main__':
    app.run(debug=True)
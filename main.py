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


def get_menu_items(user_type):
    menu_items = []

    base_dir = os.path.join(app.root_path, 'templates')

    user_type_dir = os.path.join(base_dir, user_type)
    if os.path.isdir(user_type_dir):

        files = [f for f in os.listdir(user_type_dir) if f.endswith('.html')]
        for file in files:

            name = os.path.splitext(file)[0]

            if name in ['base', 'layout', 'components']:
                continue

            display_name = name.replace('_', ' ').title()

            route_name = name
            print(route_name)

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

            icon = icon_mapping.get(name, 'fas fa-circle')

            menu_items.append({
                'name': display_name,
                'route': route_name,
                'icon': icon
            })

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


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def check_password(stored_hash, provided_password):
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
    session.clear()
    flash("Session error. Please log in again.")
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    user_type = request.args.get('user_type') or request.form.get('user_type')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return render_template('login.html', user_type=user_type)
        try:
            firebase_email_key = email.replace('.', ',')
            if user_type == 'admin':
                admin_ref = database.child(f'administrators/admins/{firebase_email_key}')
                admin_data = admin_ref.get()
                if admin_data and check_password(admin_data.get("password"), password):
                    session['user_id'] = firebase_email_key
                    session['email'] = email
                    session['user_type'] = 'admin'
                    session['name'] = admin_data.get("name", "Admin")
                    session['menu_items'] = get_menu_items('admin')
                    return redirect(url_for('dashboard'))
            elif user_type == 'teacher':
                teacher_ref = database.child(f'administrators/teachers/{firebase_email_key}')
                teacher_data = teacher_ref.get()

                if teacher_data and check_password(teacher_data.get("password"), password):
                    session['user_id'] = firebase_email_key
                    session['email'] = email
                    session['user_type'] = 'teacher'
                    session['name'] = teacher_data.get("name", "Teacher")

                    session['menu_items'] = get_menu_items('teacher')
                    return redirect(url_for('dashboard'))

            elif user_type == 'student':

                student_ref = database.child(f'students/{firebase_email_key}')
                student_data = student_ref.get()

                if student_data and check_password(student_data.get("password"), password):
                    session['user_id'] = firebase_email_key
                    session['email'] = email
                    session['user_type'] = 'student'
                    session['name'] = student_data.get("name", "Student")
                    session['active'] = student_data.get("active", False)

                    session['menu_items'] = get_menu_items('student')
                    return redirect(url_for('dashboard'))

            flash("Invalid credentials. Please try again.")
        except Exception as e:
            flash(f"Authentication error: {str(e)}")
            print(f"Login error: {str(e)}")

    return render_template('login.html', user_type=user_type)


@app.route('/quiz')
def quiz():
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


@app.route('/admin/add_subject', methods=['GET', 'POST'])
@login_required(user_types=['admin'])
def add_subject():
    subjects = []
    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        if subject_name:
            try:
                subjects_ref = database.child('subjects')
                new_subject_ref = subjects_ref.push()
                new_subject_ref.set({"name": subject_name})
                flash(f"Subject '{subject_name}' added successfully!")
            except Exception as e:
                flash(f"Error adding subject: {e}")

    try:
        subjects_ref = database.child('subjects')
        subjects_data = subjects_ref.get()
        if subjects_data:
            for key, value in subjects_data.items():
                subjects.append({"id": key, "name": value.get("name", "Unknown")})
    except Exception as e:
        flash(f"Error fetching subjects: {e}")

    return render_template('admin/add_subject.html', subjects=subjects)


@app.route('/student/')
@login_required(user_types=['student'])
def student_dashboard():
    return render_template('student/dashboard.html')


@app.route('/teacher/')
@login_required(user_types=['teacher'])
def teacher_dashboard():
    return render_template('teacher/dashboard.html')


@app.route('/teacher/generate_exam', methods=['GET', 'POST'])
@login_required(user_types=['teacher'])
def generate_exam():
    user_id = session.get('user_id')
    menu_items = get_menu_items('teacher')

    subjects = []
    try:
        subjects_ref = database.child('subjects')
        subjects_data = subjects_ref.get()
        if subjects_data:
            for key, value in subjects_data.items():
                if teacher_teaches_subject(user_id, key):
                    subjects.append({"id": key, "name": value.get("name", "Unknown")})
    except Exception as e:
        flash(f"Error fetching subjects: {e}")

    return render_template('teacher/generate_exam.html', subjects=subjects, menu_items=menu_items)


@app.route('/api/questions', methods=['GET'])
@login_required(user_types=['teacher'])
def get_questions():
    subject_id = request.args.get('subject')

    if not subject_id:
        return {'error': 'Subject ID is required'}, 400

    try:
        questions_ref = database.child('questions')
        all_questions = questions_ref.get()
        questions_list = []

        if all_questions:
            for q_id, q_data in all_questions.items():
                if q_data.get('subject_id') == subject_id:
                    questions_list.append({
                        'id': q_id,
                        'text': q_data.get('text', ''),
                        'subject_id': subject_id,
                        'question_type': q_data.get('question_type', 'mcq'),
                        'difficulty': q_data.get('difficulty', 'medium'),
                        'created_by_name': q_data.get('created_by_name', 'Unknown Teacher'),
                        'created_at': q_data.get('created_at', datetime.now().strftime('%Y-%m-%d'))
                    })

        return {'questions': questions_list}

    except Exception as e:
        return {'error': str(e)}, 500


# Add this route to save the exam
@app.route('/api/save_exam', methods=['POST'])
@login_required(user_types=['teacher'])
def save_exam():
    if not request.is_json:
        return {'error': 'Invalid request format'}, 400

    data = request.json
    user_id = session.get('user_id')
    user_name = session.get('name', 'Unknown Teacher')

    try:
        # Create exam record
        exams_ref = database.child('exams')
        new_exam_ref = exams_ref.push()

        exam_data = {
            'title': data.get('title'),
            'subject_id': data.get('subject_id'),
            'exam_type': data.get('exam_type'),
            'exam_date': data.get('exam_date'),
            'duration': data.get('duration'),
            'created_by': user_id,
            'created_by_name': user_name,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'questions': {}
        }

        # Add questions to the exam
        for index, question in data.get('questions', {}).items():
            exam_data['questions'][index] = {
                'question_id': question.get('question_id'),
                'order': question.get('order')
            }

        new_exam_ref.set(exam_data)

        return {'success': True, 'exam_id': new_exam_ref.key}

    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/teacher/submissions')
@login_required(user_types=['teacher'])
def submissions():
    return render_template('teacher/submissions.html')


@app.route('/teacher/manage_students')
@login_required(user_types=['teacher'])
def manage_students():
    return render_template('teacher/manage_students.html')


@app.route('/admin/')
@login_required(user_types=['admin'])
def admin_dashboard():
    return render_template('admin/dashboard.html')


@app.route('/profile')
@login_required()
def profile():
    user_type = session.get('user_type')
    user_id = session.get('user_id')
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
    if not session.get('user_type') == "admin":
        flash("You must be logged in to access admin panel.")
        return redirect(url_for('admin_dashboard'))
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
    if not session.get('user_type') == "admin":
        flash("You must be logged in to access admin panel.")
        return redirect(url_for('admin_dashboard'))
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
        subject_ref = database.child(f'subjects/{subject_id}')
        subject_data = subject_ref.get()

        if not subject_data or 'name' not in subject_data:
            return False

        subject_name = subject_data.get('name').lower()
        teacher_subjects = [s.lower() for s in teacher_data.get('subjects', [])]
        return subject_name in teacher_subjects

    except Exception as e:
        print(f"Error checking teacher subjects: {e}")
        return False


@app.route('/add_question', methods=['GET', 'POST'])
@login_required(user_types=['admin', 'teacher'])
def add_question():
    user_type = session.get('user_type')
    user_id = session.get('user_id')
    menu_items = get_menu_items(user_type)

    # Get all subjects based on user type
    subjects = []
    try:
        subjects_ref = database.child('subjects')
        subjects_data = subjects_ref.get()
        if subjects_data:
            for key, value in subjects_data.items():
                if user_type == 'teacher':
                    if teacher_teaches_subject(user_id, key):
                        subjects.append({"id": key, "name": value.get("name", "Unknown")})
                else:
                    subjects.append({"id": key, "name": value.get("name", "Unknown")})
    except Exception as e:
        flash(f"Error fetching subjects: {e}")

    if user_type == 'teacher' and not subjects:
        flash("You don't have any assigned subjects to add questions for. Please contact an administrator.")
        return redirect(url_for('teacher_dashboard'))

    # For admins, get all questions with filtering
    admin_questions = []
    current_page = 1
    total_pages = 1

    if user_type == 'admin':
        try:
            # Get filter parameters
            subject_filter = request.args.get('subject_filter', '')
            difficulty_filter = request.args.get('difficulty_filter', '')
            created_by_filter = request.args.get('created_by_filter', '')
            question_type_filter = request.args.get('question_type_filter', '')

            # Get all questions from database
            questions_ref = database.child('questions')
            all_questions = questions_ref.get()

            # Create a list of filtered questions
            filtered_questions = []

            if all_questions:
                # Get all users for creator name lookup
                all_teachers = database.child('administrators/teachers').get() or {}
                all_admins = database.child('administrators/admins').get() or {}
                all_students = database.child('students').get() or {}

                subject_names = {subject["id"]: subject["name"] for subject in subjects}

                for q_id, q_data in all_questions.items():
                    # Apply subject filter if specified
                    if subject_filter and q_data.get('subject_id') != subject_filter:
                        continue

                    # Apply difficulty filter if specified
                    if difficulty_filter and q_data.get('difficulty') != difficulty_filter:
                        continue

                    # Apply question type filter if specified
                    if question_type_filter and q_data.get('question_type', 'mcq') != question_type_filter:
                        continue

                    # Get creator details
                    creator_id = q_data.get('created_by', '')
                    creator_type = q_data.get('created_by_type', '')
                    creator_name = "Unknown"
                    creator_email = creator_id.replace(',', '.')

                    if creator_type == 'teacher' and creator_id in all_teachers:
                        creator_name = all_teachers[creator_id].get('name', creator_email)
                    elif creator_type == 'admin' and creator_id in all_admins:
                        creator_name = all_admins[creator_id].get('name', creator_email)
                    elif creator_type == 'student' and creator_id in all_students:
                        creator_name = all_students[creator_id].get('name', creator_email)

                    # Apply created_by filter if specified (check against name or email)
                    if created_by_filter:
                        search_term = created_by_filter.lower()
                        if (search_term not in creator_name.lower() and
                                search_term not in creator_email.lower()):
                            continue

                    # Add question to filtered list
                    filtered_questions.append({
                        'id': q_id,
                        'text': q_data.get('text', ''),
                        'subject_id': q_data.get('subject_id', ''),
                        'subject_name': subject_names.get(q_data.get('subject_id', ''), 'Unknown Subject'),
                        'difficulty': q_data.get('difficulty', 'medium'),
                        'question_type': q_data.get('question_type', 'mcq'),
                        'options': q_data.get('options', {}),
                        'correct_answer': q_data.get('correct_answer', ''),
                        'blanks': q_data.get('blanks', []),
                        'column_a': q_data.get('column_a', {}),
                        'column_b': q_data.get('column_b', {}),
                        'matches': q_data.get('matches', {}),
                        'assertion': q_data.get('assertion', ''),
                        'reason': q_data.get('reason', ''),
                        'ar_correct_option': q_data.get('ar_correct_option', ''),
                        'case_content': q_data.get('case_content', ''),
                        'case_questions': q_data.get('case_questions', []),
                        'created_by': creator_id,
                        'created_by_name': creator_name,
                        'created_by_type': creator_type,
                        'created_at': q_data.get('created_at', '')
                    })

            # Pagination
            page = int(request.args.get('page', 1))
            items_per_page = 10
            total_items = len(filtered_questions)
            total_pages = (total_items + items_per_page - 1) // items_per_page

            # Ensure page is within valid range
            page = max(1, min(page, total_pages)) if total_pages > 0 else 1
            current_page = page

            # Get questions for current page
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            admin_questions = filtered_questions[start_idx:end_idx]

        except Exception as e:
            flash(f"Error fetching questions: {e}")

    # For teachers, only get their own questions
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
                            'question_type': q_data.get('question_type', 'mcq'),
                            'options': q_data.get('options', {}),
                            'correct_answer': q_data.get('correct_answer', ''),
                            'blanks': q_data.get('blanks', []),
                            'column_a': q_data.get('column_a', {}),
                            'column_b': q_data.get('column_b', {}),
                            'matches': q_data.get('matches', {}),
                            'assertion': q_data.get('assertion', ''),
                            'reason': q_data.get('reason', ''),
                            'ar_correct_option': q_data.get('ar_correct_option', ''),
                            'case_content': q_data.get('case_content', ''),
                            'case_questions': q_data.get('case_questions', []),
                            'created_at': q_data.get('created_at', '')
                        })
        except Exception as e:
            flash(f"Error fetching questions: {e}")

    # Handle POST request to add a new question
    if request.method == 'POST':
        subject_id = request.form.get('subject')
        question_type = request.form.get('question_type', 'mcq')
        difficulty = request.form.get('difficulty')

        if not all([subject_id, question_type, difficulty]):
            flash("Basic question information is required.")
            return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                   admin_questions=admin_questions, current_page=current_page,
                                   total_pages=total_pages, menu_items=menu_items)

        # If teacher, verify they teach the subject
        if user_type == 'teacher' and not teacher_teaches_subject(user_id, subject_id):
            flash("You are not authorized to add questions for this subject.")
            return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                   menu_items=menu_items)

        # Base question data
        question_data = {
            "subject_id": subject_id,
            "question_type": question_type,
            "difficulty": difficulty,
            "created_by": user_id,
            "created_by_type": user_type,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Add question-type specific data
        if question_type == 'mcq':
            question_text = request.form.get('question_text')
            option1 = request.form.get('option1')
            option2 = request.form.get('option2')
            option3 = request.form.get('option3')
            option4 = request.form.get('option4')
            correct_answer = request.form.get('correct_answer')

            if not all([question_text, option1, option2, option3, option4, correct_answer]):
                flash("All fields for MCQ are required.")
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages, menu_items=menu_items)

            question_data.update({
                "text": question_text,
                "options": {
                    "1": option1,
                    "2": option2,
                    "3": option3,
                    "4": option4
                },
                "correct_answer": correct_answer,
            })

        elif question_type == 'fill_in_blanks':
            question_text = request.form.get('fitb_text')

            # Get all blanks from form
            blanks = []
            i = 1
            while True:
                blank = request.form.get(f'blank{i}')
                if blank is None:
                    break
                blanks.append(blank)
                i += 1

            if not question_text or not blanks:
                flash("Question text and at least one blank are required.")
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages, menu_items=menu_items)

            question_data.update({
                "text": question_text,
                "blanks": blanks
            })

        elif question_type == 'match_columns':
            # Get column items from form
            column_a = {}
            column_b = {}
            matches = {}

            i = 1
            while True:
                item_a = request.form.get(f'column_a_{i}')
                item_b = request.form.get(f'column_b_{i}')

                if item_a is None or item_b is None:
                    break

                column_a[str(i)] = item_a
                column_b[str(i)] = item_b
                matches[str(i)] = str(i)  # Default matching
                i += 1

            if not column_a or not column_b:
                flash("At least one pair of matching items is required.")
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages, menu_items=menu_items)

            question_data.update({
                "text": "Match the following items:",
                "column_a": column_a,
                "column_b": column_b,
                "matches": matches
            })

        elif question_type == 'assertion_reason':
            assertion = request.form.get('assertion')
            reason = request.form.get('reason')
            ar_correct_option = request.form.get('ar_correct_option')

            if not assertion or not reason or not ar_correct_option:
                flash("Assertion, reason, and correct option are required.")
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages, menu_items=menu_items)

            question_data.update({
                "text": "Assertion and Reason Question",
                "assertion": assertion,
                "reason": reason,
                "ar_correct_option": ar_correct_option
            })

        elif question_type == 'case_based':
            case_content = request.form.get('case_content')

            if not case_content:
                flash("Case content is required.")
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages, menu_items=menu_items)

            # Process sub-questions for the case
            case_questions = []
            i = 1
            while True:
                sub_question = request.form.get(f'case_question_{i}')
                if not sub_question:
                    break

                # Get options for this sub-question
                options = {}
                for j in range(1, 5):
                    option = request.form.get(f'case_q{i}_option{j}')
                    if option:
                        options[str(j)] = option

                correct_answer = request.form.get(f'case_q{i}_correct')

                if sub_question and options and correct_answer:
                    case_questions.append({
                        'text': sub_question,
                        'options': options,
                        'correct_answer': correct_answer
                    })

                i += 1

            if not case_questions:
                flash("At least one case-based question is required.")
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages, menu_items=menu_items)

            question_data.update({
                "text": "Case-based Questions",
                "case_content": case_content,
                "case_questions": case_questions
            })

        try:
            # Add question to database
            questions_ref = database.child('questions')
            new_question_ref = questions_ref.push()
            new_question_ref.set(question_data)
            flash("Question added successfully!")
            return redirect(url_for('add_question'))
        except Exception as e:
            flash(f"Error adding question: {e}")

    return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                           admin_questions=admin_questions, current_page=current_page,
                           total_pages=total_pages, menu_items=menu_items)


@app.route('/get_question_metadata/<question_id>')
@login_required(user_types=['admin', 'teacher'])
def get_question_metadata(question_id):
    try:
        # Get question data from the database
        question_ref = database.child('questions').child(question_id)
        question_data = question_ref.get()

        if not question_data:
            return "<div class='alert alert-danger'>Question not found</div>", 404

        # Get subject name
        subject_name = "Unknown"
        try:
            subject_id = question_data.get('subject_id')
            if subject_id:
                subject_ref = database.child('subjects').child(subject_id)
                subject_data = subject_ref.get()
                if subject_data:
                    subject_name = subject_data.get('name', 'Unknown')
        except Exception as e:
            app.logger.error(f"Error getting subject name: {e}")

        # Get creator details
        creator_id = question_data.get('created_by', '')
        creator_type = question_data.get('created_by_type', '')
        creator_name = "Unknown"

        if creator_id and creator_type:
            try:
                if creator_type == 'teacher':
                    creator_ref = database.child('administrators/teachers').child(creator_id)
                elif creator_type == 'admin':
                    creator_ref = database.child('administrators/admins').child(creator_id)
                elif creator_type == 'student':
                    creator_ref = database.child('students').child(creator_id)

                creator_data = creator_ref.get()
                if creator_data:
                    creator_name = creator_data.get('name', creator_id)
            except Exception as e:
                app.logger.error(f"Error getting creator details: {e}")

        # Prepare metadata
        metadata = {
            "subject_name": subject_name,
            "question_type": question_data.get('question_type', 'mcq'),
            "difficulty": question_data.get('difficulty', 'medium'),
            "created_by": creator_id,
            "created_by_name": creator_name,
            "created_by_type": creator_type,
            "created_at": question_data.get('created_at', '')
        }

        # Map question types to display names
        question_type_names = {
            'mcq': 'Multiple Choice',
            'fill_in_blanks': 'Fill in the Blanks',
            'match_columns': 'Match the Columns',
            'assertion_reason': 'Assertion Reason',
            'case_based': 'Case Based'
        }

        # Map difficulty to badge classes
        difficulty_classes = {
            'easy': 'bg-success',
            'medium': 'bg-warning',
            'hard': 'bg-danger'
        }

        # Generate HTML for the modal
        html = f"""
        <div class="card">
            <div class="card-body">
                <h6 class="card-subtitle mb-3 text-muted">Question Metadata</h6>

                <table class="table">
                    <tbody>
                        <tr>
                            <th style="width: 30%">Subject</th>
                            <td>{metadata['subject_name']}</td>
                        </tr>
                        <tr>
                            <th>Question Type</th>
                            <td>{question_type_names.get(metadata['question_type'], metadata['question_type'])}</td>
                        </tr>
                        <tr>
                            <th>Difficulty</th>
                            <td><span class="badge {difficulty_classes.get(metadata['difficulty'], 'bg-secondary')}">
                                {metadata['difficulty'].upper()}
                            </span></td>
                        </tr>
                        <tr>
                            <th>Created By</th>
                            <td>
                                {metadata['created_by_name']}
                                <small class="d-block text-muted">{metadata['created_by_type'].capitalize()}</small>
                            </td>
                        </tr>
                        <tr>
                            <th>Created At</th>
                            <td>{metadata['created_at']}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        """

        return html

    except Exception as e:
        app.logger.error(f"Error fetching question metadata: {e}")
        return f"<div class='alert alert-danger'>Failed to fetch question metadata: {str(e)}</div>", 500


@app.route('/edit_question/<question_id>', methods=['GET', 'POST'])
@login_required(user_types=['admin', 'teacher'])
def edit_question(question_id):
    user_type = session.get('user_type')
    user_id = session.get('user_id')
    menu_items = get_menu_items(user_type)
    try:
        question_ref = database.child(f'questions/{question_id}')
        question_data = question_ref.get()
        if not question_data:
            flash("Question not found.")
            return redirect(url_for('add_question'))

        if user_type == 'teacher' and question_data.get('created_by') != user_id:
            flash("You do not have permission to edit this question.")
            return redirect(url_for('add_question'))

        subjects = []
        try:
            subjects_ref = database.child('subjects')
            subjects_data = subjects_ref.get()
            if subjects_data:
                for key, value in subjects_data.items():
                    if user_type == 'teacher':
                        if teacher_teaches_subject(user_id, key):
                            subjects.append({"id": key, "name": value.get("name", "Unknown")})
                    else:
                        subjects.append({"id": key, "name": value.get("name", "Unknown")})
        except Exception as e:
            flash(f"Error fetching subjects: {e}")

        if request.method == 'POST':
            subject_id = request.form.get('subject')
            difficulty = request.form.get('difficulty')
            question_type = question_data.get('question_type', 'mcq')  # Get original question type

            if not all([subject_id, difficulty]):
                flash("Subject and difficulty are required.")
                return render_template('edit_question.html', question=question_data, question_id=question_id,
                                       subjects=subjects, menu_items=menu_items)

            # Base update data
            updated_data = {
                "subject_id": subject_id,
                "difficulty": difficulty,
                "updated_by": user_id,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Add question-type specific data
            if question_type == 'mcq':
                question_text = request.form.get('question_text')
                option1 = request.form.get('option1')
                option2 = request.form.get('option2')
                option3 = request.form.get('option3')
                option4 = request.form.get('option4')
                correct_answer = request.form.get('correct_answer')

                if not all([question_text, option1, option2, option3, option4, correct_answer]):
                    flash("All fields for MCQ are required.")
                    return render_template('edit_question.html', question=question_data, question_id=question_id,
                                           subjects=subjects, menu_items=menu_items)

                updated_data.update({
                    "text": question_text,
                    "options": {
                        "1": option1,
                        "2": option2,
                        "3": option3,
                        "4": option4
                    },
                    "correct_answer": correct_answer
                })

            elif question_type == 'fill_in_blanks':
                question_text = request.form.get('fitb_text')

                # Get all blanks from form
                blanks = []
                i = 1
                while True:
                    blank = request.form.get(f'blank{i}')
                    if blank is None:
                        break
                    blanks.append(blank)
                    i += 1

                if not question_text or not blanks:
                    flash("Question text and at least one blank are required.")
                    return render_template('edit_question.html', question=question_data, question_id=question_id,
                                           subjects=subjects, menu_items=menu_items)

                updated_data.update({
                    "text": question_text,
                    "blanks": blanks
                })

            elif question_type == 'match_columns':
                # Get column items from form
                column_a = {}
                column_b = {}
                matches = {}

                # Determine the number of matches from the existing data
                num_pairs = len(question_data.get('column_a', {}))

                for i in range(1, num_pairs + 1):
                    item_a = request.form.get(f'column_a_{i}')
                    item_b = request.form.get(f'column_b_{i}')

                    if item_a and item_b:
                        column_a[str(i)] = item_a
                        column_b[str(i)] = item_b
                        matches[str(i)] = str(i)  # Keep original matching

                if not column_a or not column_b:
                    flash("At least one pair of matching items is required.")
                    return render_template('edit_question.html', question=question_data, question_id=question_id,
                                           subjects=subjects, menu_items=menu_items)

                updated_data.update({
                    "text": "Match the following items:",
                    "column_a": column_a,
                    "column_b": column_b,
                    "matches": matches
                })

            elif question_type == 'assertion_reason':
                assertion = request.form.get('assertion')
                reason = request.form.get('reason')
                ar_correct_option = request.form.get('ar_correct_option')

                if not assertion or not reason or not ar_correct_option:
                    flash("Assertion, reason, and correct option are required.")
                    return render_template('edit_question.html', question=question_data, question_id=question_id,
                                           subjects=subjects, menu_items=menu_items)

                updated_data.update({
                    "text": "Assertion and Reason Question",
                    "assertion": assertion,
                    "reason": reason,
                    "ar_correct_option": ar_correct_option
                })

            elif question_type == 'case_based':
                case_content = request.form.get('case_content')

                if not case_content:
                    flash("Case content is required.")
                    return render_template('edit_question.html', question=question_data, question_id=question_id,
                                           subjects=subjects, menu_items=menu_items)

                # Process sub-questions for the case
                case_questions = []
                num_questions = len(question_data.get('case_questions', []))

                for i in range(1, num_questions + 1):
                    sub_question = request.form.get(f'case_question_{i}')
                    if not sub_question:
                        continue

                    # Get options for this sub-question
                    options = {}
                    for j in range(1, 5):
                        option = request.form.get(f'case_q{i}_option{j}')
                        if option:
                            options[str(j)] = option

                    correct_answer = request.form.get(f'case_q{i}_correct')

                    if sub_question and options and correct_answer:
                        case_questions.append({
                            'text': sub_question,
                            'options': options,
                            'correct_answer': correct_answer
                        })

                if not case_questions:
                    flash("At least one case-based question is required.")
                    return render_template('edit_question.html', question=question_data, question_id=question_id,
                                           subjects=subjects, menu_items=menu_items)

                updated_data.update({
                    "text": "Case-based Questions",
                    "case_content": case_content,
                    "case_questions": case_questions
                })

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
        question_ref = database.child(f'questions/{question_id}')
        question_data = question_ref.get()
        if not question_data:
            flash("Question not found.")
            return redirect(url_for('add_question'))

        if user_type == 'teacher' and question_data.get('created_by') != user_id:
            flash("You do not have permission to delete this question.")
            return redirect(url_for('add_question'))

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


@app.context_processor
def inject_menu_items():
    if 'menu_items' in session:
        return {'menu_items': session.get('menu_items', [])}
    elif 'user_type' in session:

        menu_items = get_menu_items(session.get('user_type'))
        session['menu_items'] = menu_items
        return {'menu_items': menu_items}
    return {'menu_items': []}


if __name__ == '__main__':
    app.run(debug=True)

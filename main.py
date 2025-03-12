from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, db
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Firebase configuration and initialization
try:
    # Check if the app is already initialized
    firebase_admin.get_app()
except ValueError:
    # Get the current directory of the file
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Path to service account file
    service_account_path = os.path.join(current_dir, 'serviceAccountKey.json')

    # Initialize the app with credentials from file
    firebase_credentials = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(firebase_credentials, {
        'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
    })

# Database reference
database = db.reference('/')


@app.route('/')
def index():
    return render_template('index.html')


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

    return render_template('quiz.html', subjects=subjects)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            # Check admin credentials against Firebase
            admin_ref = database.child('admins')
            admin_data = admin_ref.get()
            if admin_data:
                for key, value in admin_data.items():
                    if value.get("username") == username and value.get("password") == password:
                        session['admin'] = True
                        return redirect(url_for('admin_interface'))

            flash("Invalid credentials. Please try again.")
        except Exception as e:
            flash(f"Authentication error: {e}")

    return render_template('admin.html')


@app.route('/admin_interface')
def admin_interface():
    if not session.get('admin'):
        flash("You must be logged in to access admin panel.")
        return redirect(url_for('admin'))

    return render_template('admin_interface.html')


@app.route('/add_subject', methods=['GET', 'POST'])
def add_subject():
    if not session.get('admin'):
        flash("You must be logged in to access admin panel.")
        return redirect(url_for('admin'))

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

    return render_template('add_subject.html', subjects=subjects)


@app.route('/delete_subject/<subject_id>')
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


@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if not session.get('admin'):
        flash("You must be logged in to access admin panel.")
        return redirect(url_for('admin'))

    # Get subjects for dropdown
    subjects = []
    try:
        subjects_ref = database.child('subjects')
        subjects_data = subjects_ref.get()
        if subjects_data:
            for key, value in subjects_data.items():
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
            return render_template('add_question.html', subjects=subjects)

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
            "difficulty": difficulty
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

    return render_template('add_question.html', subjects=subjects)


@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash("You have been logged out.")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
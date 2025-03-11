from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyrebase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-replace-in-production')

# Firebase configuration
firebase_config = {
    "apiKey": os.getenv('FIREBASE_API_KEY'),
    "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
    "projectId": os.getenv('FIREBASE_PROJECT_ID'),
    "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
    "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
    "appId": os.getenv('FIREBASE_APP_ID'),
    "databaseURL": os.getenv('FIREBASE_DATABASE_URL')
}
print(os.getenv('FIREBASE_API_KEY'))
# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# Get all data from the root of your database
all_data = db.get()

# Print all data
print("All data in database:")
for key in all_data.each():
    print(f"Key: {key.key()}")
    print(f"Value: {key.val()}")
    print("-" * 30)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/quiz')
def quiz():
    # Get subjects from Firebase for dropdown
    subjects = []
    try:
        subject_data = db.child("subjects").get().val()
        if subject_data:
            for key, value in subject_data.items():
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
            admin_data = db.child("admins").get().val()
            print(admin_data)
            if admin_data:
                for key, value in admin_data.items():
                    print(key, "key")
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
                db.child("subjects").push({"name": subject_name})
                flash(f"Subject '{subject_name}' added successfully!")
            except Exception as e:
                flash(f"Error adding subject: {e}")

    # Get current subjects
    try:
        subject_data = db.child("subjects").get().val()
        if subject_data:
            for key, value in subject_data.items():
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
        db.child("subjects").child(subject_id).remove()
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
            db.child("subjects").child(subject_id).update({"name": new_name})
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
        subject_data = db.child("subjects").get().val()
        if subject_data:
            for key, value in subject_data.items():
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
            db.child("questions").push(question_data)
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
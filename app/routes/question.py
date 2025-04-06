from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, \
    render_template_string
from app.utils.auth import login_required
from app.models.question import (
    get_teacher_questions, get_admin_questions, get_question_by_id,
    add_question as model_add_question, update_question, delete_question as delete_in_db,
    process_question_data
)
from app.models.subject import teacher_teaches_subject
from datetime import datetime

from app.utils.database import database

question_bp = Blueprint('question', __name__)


@question_bp.route('/add_question', methods=['GET', 'POST'])
@login_required(user_types=['admin', 'teacher'])
def add_question():
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    # Get all subjects based on user type
    subjects = session['subjects']

    if user_type == 'teacher' and not subjects:
        flash("You don't have any assigned subjects to add questions for. Please contact an administrator.", 'warning')
        return redirect(url_for('common.teacher_dashboard'))

    # Initialize questions lists
    admin_questions = []
    teacher_questions = []
    current_page = 1
    total_pages = 1

    # For admins, get all questions with filtering
    if user_type == 'admin':
        try:
            # Get filter parameters
            filters = {
                'subject_filter': request.args.get('subject_filter', ''),
                'difficulty_filter': request.args.get('difficulty_filter', ''),
                'created_by_filter': request.args.get('created_by_filter', ''),
                'question_type_filter': request.args.get('question_type_filter', '')
            }

            # Get page for pagination
            page = int(request.args.get('page', 1))

            # Get filtered questions
            result = get_admin_questions(filters, page)
            admin_questions = result['questions']
            current_page = result['current_page']
            total_pages = result['total_pages']

        except Exception as e:
            flash(f"Error fetching questions: {e}", 'danger')

    # For teachers, only get their own questions
    if user_type == 'teacher':
        try:
            teacher_questions = get_teacher_questions(user_id)
        except Exception as e:
            flash(f"Error fetching questions: {e}", 'danger')

    # Handle POST request to add a new question
    if request.method == 'POST':
        subject_id = request.form.get('subject')

        # If teacher, verify they teach the subject
        if user_type == 'teacher' and not teacher_teaches_subject(user_id, subject_id):
            flash("You are not authorized to add questions for this subject.", 'warning')
            return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions)

        # Process the form data
        question_data, error = process_question_data(request.form, user_id, user_type)

        if error:
            flash(error, 'warning')
            return render_template('add_question.html', subjects=subjects,
                                   teacher_questions=teacher_questions,
                                   admin_questions=admin_questions,
                                   current_page=current_page,
                                   total_pages=total_pages)

        # Add timestamp for new questions
        question_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Add question to database using the model function
            success = model_add_question(question_data)
            if success:
                if user_type == 'teacher':
                    teacher_ref = database.child('administrators').child('teachers').child(user_id)
                    current_count = teacher_ref.child('questions_created').get()
                    teacher_ref.update({'questions_created': current_count + 1})
                flash("Question deleted successfully!", 'success')
                return redirect(url_for('question.add_question'))
            else:
                flash("Error adding question. Please try again.", 'danger')
        except Exception as e:
            flash(f"Error adding question: {e}", 'danger')

    return render_template('add_question.html', subjects=subjects,
                           teacher_questions=teacher_questions,
                           admin_questions=admin_questions,
                           current_page=current_page,
                           total_pages=total_pages)


@question_bp.route('/get_question_metadata/<question_id>')
@login_required(user_types=['admin', 'teacher'])
def get_question_metadata(question_id):
    try:
        question_data = get_question_by_id(question_id)
        subject_id = question_data.get('subject_id')

        # Get subject name from session
        subject_name = "Unknown"
        for subject in session.get('subjects', []):
            if subject.get('id') == subject_id:
                subject_name = subject.get('name')
                break
        question_data['created_by'] = question_data['created_by'].replace(',', '.')
        # HTML template for success
        html_content = render_template_string('''
            <div class="container mt-4">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        Question Metadata
                    </div>
                    <div class="card-body">
                        {% if data %}
                            <p><strong>Text:</strong> {{ data.text }}</p>
                            <p><strong>Class:</strong> {{ data.class }}</p>
                            <p><strong>Subject:</strong> {{ subject_name }}</p>
                            <p><strong>Marks:</strong> {{ data.marks }}</p>
                            <p><strong>Type:</strong> {{ data.question_type }}</p>
                            <p><strong>Difficulty:</strong> {{ data.difficulty }}</p>
                            <p><strong>By:</strong> {{ data.created_by }}</p>
                            {% else %}
                            <p>No question data found.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        ''', data=question_data, subject_name=subject_name)

        return html_content

    except Exception as e:
        # HTML template for error
        error_html = render_template_string('''
            <div class="container mt-4">
                <div class="alert alert-danger" role="alert">
                    <strong>Error:</strong> {{ error }}
                </div>
            </div>
        ''', error=str(e))

        return error_html


@question_bp.route('/edit_question/<question_id>', methods=['GET', 'POST'])
@login_required(user_types=['admin', 'teacher'])
def edit_question(question_id):
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    try:
        # Get the question data
        question_data = get_question_by_id(question_id)

        if not question_data:
            flash("Question not found.", 'danger')
            return redirect(url_for('question.add_question'))

        # Check if user is authorized to edit this question
        if user_type == 'teacher' and str(question_data.get('created_by')) != str(user_id):
            flash("You are not authorized to edit this question.", 'danger')
            return redirect(url_for('question.add_question'))

        # Get subjects based on user type
        subjects = session['subjects']

        if request.method == 'POST':
            subject_id = request.form.get('subject')

            # If teacher, verify they teach the subject
            if user_type == 'teacher' and subject_id != question_data.get('subject_id') and not teacher_teaches_subject(
                    user_id, subject_id):
                flash("You are not authorized to move this question to the selected subject.", 'warning')
                return render_template('edit_question.html', question=question_data, subjects=subjects,
                                       question_id=question_id)

            # Process the form data with existing question data for structure reference
            updated_data, error = process_question_data(request.form, user_id, user_type, question_data)

            if error:
                flash(error, 'warning')
                return render_template('edit_question.html', question=question_data, subjects=subjects,
                                       question_id=question_id)

            # Update the question in the database
            success = update_question(question_id, updated_data)
            if success:
                flash("Question updated successfully!", 'success')
                return redirect(url_for('question.add_question'))
            else:
                flash("Error updating question. Please try again.", 'danger')

    except Exception as e:
        flash(f"Error: {e}", 'danger')
        return redirect(url_for('question.add_question'))

    return render_template('edit_question.html', question=question_data, subjects=subjects, question_id=question_id)


@question_bp.route('/delete_question/<question_id>')
@login_required(user_types=['admin', 'teacher'])
def delete_question(question_id):
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    try:
        # Get the question data
        question_data = get_question_by_id(question_id)

        if not question_data:
            flash("Question not found.", 'danger')
            return redirect(url_for('question.add_question'))

        # Check if user is authorized to delete this question
        if user_type == 'teacher' and question_data.get('created_by') != user_id:
            flash("You are not authorized to delete this question.", 'danger')
            return redirect(url_for('question.add_question'))

        # Delete the question
        success = delete_in_db(question_id)
        if success:
            if user_type == 'teacher':
                teacher_ref = database.child('administrators').child('teachers').child(user_id)
                current_count = teacher_ref.child('questions_created').get()
                teacher_ref.update({'questions_created': current_count - 1})
            flash("Question deleted successfully!", 'success')
        else:
            flash("Error deleting question. Please try again.", 'danger')

    except Exception as e:
        flash(f"Error: {e}", 'danger')

    return redirect(url_for('question.add_question'))
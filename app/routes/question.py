import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, \
    render_template_string
from app.utils.auth import login_required
from app.models.question import (
    get_teacher_questions, get_admin_questions, get_question_by_id,
    add_question as model_add_question, update_question, delete_question,
)
from app.models.subject import teacher_teaches_subject
from datetime import datetime

question_bp = Blueprint('question', __name__)


@question_bp.route('/add_question', methods=['GET', 'POST'])
@login_required(user_types=['admin', 'teacher'])
def add_question():
    print(session)
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
        question_type = request.form.get('question_type', 'mcq')
        difficulty = request.form.get('difficulty')
        class_of_question = request.form.get('class', '')  # Added class parameter

        if not all([subject_id, question_type, difficulty]):
            flash("Basic question information is required.", 'warning')
            return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                   admin_questions=admin_questions, current_page=current_page,
                                   total_pages=total_pages)

        # If teacher, verify they teach the subject
        if user_type == 'teacher' and not teacher_teaches_subject(user_id, subject_id):
            flash("You are not authorized to add questions for this subject.", 'warning')
            return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions)

        # Base question data
        question_data = {
            "subject_id": subject_id,
            "question_type": question_type,
            "difficulty": difficulty,
            "class": int(class_of_question),  # Added class field
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
                flash("All fields for MCQ are required.", 'warning')
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages)

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
                flash("Question text and at least one blank are required.", 'warning')
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages)

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
                flash("At least one pair of matching items is required.", 'warning')
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages)

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
                flash("Assertion, reason, and correct option are required.", 'warning')
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages)

            question_data.update({
                "text": "Assertion and Reason Question",
                "assertion": assertion,
                "reason": reason,
                "ar_correct_option": ar_correct_option
            })

        elif question_type == 'case_based':
            case_content = request.form.get('case_content')

            if not case_content:
                flash("Case content is required.", 'warning')
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages)

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
                flash("At least one case-based question is required.", 'warning')
                return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                                       admin_questions=admin_questions, current_page=current_page,
                                       total_pages=total_pages)

            question_data.update({
                "text": "Case-based Questions",
                "case_content": case_content,
                "case_questions": case_questions
            })

        try:
            # Add question to database using the model function
            success = model_add_question(question_data)
            if success:
                flash("Question added successfully!", 'danger')
                return redirect(url_for('question.add_question'))
            else:
                flash("Error adding question. Please try again.", 'danger')
        except Exception as e:
            flash(f"Error adding question: {e}", 'danger')
    t2 = time.perf_counter()
    return render_template('add_question.html', subjects=subjects, teacher_questions=teacher_questions,
                           admin_questions=admin_questions, current_page=current_page,
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
        if user_type == 'teacher' and question_data.get('created_by') != user_id:
            flash("You are not authorized to edit this question.", 'danger')
            return redirect(url_for('question.add_question'))

        # Get subjects based on user type
        subjects = session['subjects']

        if request.method == 'POST':
            # Update the question data
            subject_id = request.form.get('subject')
            question_type = question_data.get('question_type')  # Question type cannot be changed
            difficulty = request.form.get('difficulty')
            class_of_question = request.form.get('class', question_data.get('class', ''))

            # If teacher, verify they teach the subject
            if user_type == 'teacher' and subject_id != question_data.get('subject_id') and not teacher_teaches_subject(
                    user_id, subject_id):
                flash("You are not authorized to move this question to the selected subject.", 'warning')
                return render_template('edit_question.html', question=question_data, subjects=subjects)

            # Base updated data
            updated_data = {
                "subject_id": subject_id,
                "difficulty": difficulty,
                "class": class_of_question
            }

            # Update question-type specific data
            if question_type == 'mcq':
                question_text = request.form.get('question_text')
                option1 = request.form.get('option1')
                option2 = request.form.get('option2')
                option3 = request.form.get('option3')
                option4 = request.form.get('option4')
                correct_answer = request.form.get('correct_answer')

                if not all([question_text, option1, option2, option3, option4, correct_answer]):
                    flash("All fields for MCQ are required.", 'warning')
                    return render_template('edit_question.html', question=question_data, subjects=subjects)

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
                    flash("Question text and at least one blank are required.", 'warning')
                    return render_template('edit_question.html', question=question_data, subjects=subjects)

                updated_data.update({
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
                    flash("At least one pair of matching items is required.", 'warning')
                    return render_template('edit_question.html', question=question_data, subjects=subjects)

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
                    flash("Assertion, reason, and correct option are required.", 'warning')
                    return render_template('edit_question.html', question=question_data, subjects=subjects)

                updated_data.update({
                    "assertion": assertion,
                    "reason": reason,
                    "ar_correct_option": ar_correct_option
                })

            elif question_type == 'case_based':
                case_content = request.form.get('case_content')

                if not case_content:
                    flash("Case content is required.", 'warning')
                    return render_template('edit_question.html', question=question_data, subjects=subjects)

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
                    flash("At least one case-based question is required.", 'warning')
                    return render_template('edit_question.html', question=question_data, subjects=subjects)

                updated_data.update({
                    "case_content": case_content,
                    "case_questions": case_questions
                })

            # Update the question in the database
            success = update_question(question_id, updated_data)
            if success:
                flash("Question updated successfully!", 'primary')
                return redirect(url_for('question.add_question'))
            else:
                flash("Error updating question. Please try again.", 'danger')

    except Exception as e:
        flash(f"Error: {e}", 'danger')
        return redirect(url_for('question.add_question'))

    return render_template('edit_question.html', question=question_data, subjects=subjects)


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
        success = delete_question(question_id)
        if success:
            flash("Question deleted successfully!", 'primary')
        else:
            flash("Error deleting question. Please try again.", 'danger')

    except Exception as e:
        flash(f"Error: {e}", 'danger')

    return redirect(url_for('question.add_question'))
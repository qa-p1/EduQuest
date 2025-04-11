from flask import Blueprint, render_template, session, request, redirect, url_for, flash, jsonify
from app.utils.auth import login_required
from app.models.exam import get_student_exams, get_exam_by_id, check_submission_exists, save_exam_submission
from app.utils.database import database
import uuid
import datetime

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/')
@login_required(user_types=['student'])
def dashboard():
    return render_template('student/dashboard.html')



@student_bp.route('/exams')
@login_required(user_types=['student'])
def exams():
    student_id = session.get('user_id')
    print(student_id)
    student_ref = database.child('students').child(student_id.replace('.', ','))
    student_data = student_ref.get()
    student_class = student_data['class']
    student_section = student_data['section']

    student_status = student_data.get('status', 'inactive') if student_data else 'inactive'

    # Get available exams
    exams_data = get_student_exams(student_id, student_class, student_section)

    return render_template('student/exams.html',
                           exams=exams_data,
                           student_status=student_status)


@student_bp.route('/take_exam/<exam_id>')
@login_required(user_types=['student'])
def take_exam(exam_id):
    student_id = session.get('user_id')

    # Get student status from database
    student_ref = database.child('students').child(student_id.replace('.', ','))
    student_data = student_ref.get()
    student_status = student_data.get('status', 'inactive') if student_data else 'inactive'

    if student_status != 'active':
        flash("Your account is not active. Please contact your teacher.", "warning")
        return redirect(url_for('student.exams'))

    # Check if student has already submitted this exam
    if check_submission_exists(exam_id, student_id):
        flash("You have already submitted this exam.", "info")
        return redirect(url_for('student.exams'))

    # Get exam details
    exam_data = get_exam_by_id(exam_id)
    if not exam_data:
        flash("Exam not found.", "danger")
        return redirect(url_for('student.exams'))

    # Check if exam is active
    if not exam_data.get('exam_status', False):
        flash("This exam is not currently active.", "warning")
        return redirect(url_for('student.exams'))

    # Get questions for the exam
    questions = []
    for q_item in exam_data.get('questions', []):
        question_id = q_item.get('question_id')
        question_data = database.child('questions').child(question_id).get()
        if question_data:
            question_data['id'] = question_id
            questions.append(question_data)

    return render_template('take_exam.html',
                           exam=exam_data,
                           questions=questions,
                           duration=int(exam_data.get('duration', 60)))


@student_bp.route('/submit_exam/<exam_id>', methods=['POST'])
@login_required(user_types=['student'])
def submit_exam(exam_id):
    student_id = session.get('user_id')
    student_email = session.get('user_id')

    # Get student status from database
    student_ref = database.child('students').child(student_id.replace('.', ','))
    student_data = student_ref.get()
    student_status = student_data.get('status', 'inactive') if student_data else 'inactive'

    if student_status != 'active':
        return jsonify({'status': 'error', 'message': 'Your account is not active'})

    # Check if student has already submitted this exam
    if check_submission_exists(exam_id, student_id):
        return jsonify({'status': 'error', 'message': 'You have already submitted this exam'})

    # Process submitted answers
    answers = {}
    for key, value in request.form.items():
        if key.startswith('answer_'):
            question_id = key.replace('answer_', '')
            answers[question_id] = value

    # Create submission data
    submission_id = str(uuid.uuid4())
    submission_data = {
        'student_id': student_id,
        'student_email': student_email,
        'exam_id': exam_id,
        'answers': answers,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Save submission
    if save_exam_submission(exam_id, student_id, submission_id, submission_data):
        return jsonify({'status': 'success', 'message': 'Exam submitted successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to submit exam'})

@student_bp.route('/get_subject_name/<subject_id>')
@login_required(user_types=['student'])
def get_subject_name(subject_id):
    try:
        subject_ref = database.child('subjects').child(subject_id)
        subject_data = subject_ref.get()
        subject_name = subject_data.get('name', subject_id) if subject_data else subject_id
        return jsonify({'name': subject_name})
    except Exception as e:
        print(f"Error fetching subject name: {e}")
        return jsonify({'name': subject_id})
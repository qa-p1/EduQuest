import time
from datetime import datetime
from flask import Blueprint, render_template, session, request, flash, jsonify
from app.utils.auth import login_required
from app.utils.database import database
from app.models.teacher_services import (
    get_teacher_data, get_teacher_classes, create_exam, get_teacher_exams,
    update_exam_status, get_students_by_class_section, get_class_section_pairs,
    update_student_status, update_bulk_student_status, manage_submission,
    get_total_students, get_subject_name, calculate_completion_percentage
)

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


@teacher_bp.route('/')
@login_required(user_types=['teacher'])
def dashboard():
    return render_template('teacher/dashboard.html')


@teacher_bp.route('/generate_exam', methods=['GET', 'POST'])
@login_required(user_types=['teacher'])
def generate_exam():
    if request.method == 'POST':
        if not request.is_json:
            return {'error': 'Invalid request format'}, 400

        data = request.json
        user_id = session.get('user_id')
        user_name = session.get('name', 'Unknown Teacher')

        try:
            exam_id = create_exam(data, user_id, user_name)
            flash('Exam created successfully!', 'success')
            return jsonify({'success': True, 'exam_id': exam_id})
        except Exception as e:
            return {'error': str(e)}, 500

    # GET request - render the form
    return render_template('teacher/generate_exam.html', subjects=session['subjects'])


@teacher_bp.route('/api/subjects_by_class', methods=['GET'])
@login_required(user_types=['teacher'])
def get_subjects_by_class():
    class_id = request.args.get('class')
    if not class_id:
        return {'error': 'Class ID is required'}, 400

    try:
        user_email = session.get('user_id')
        teacher_data = get_teacher_data(user_email)

        if not teacher_data or 'classes_teached' not in teacher_data:
            return {'subjects': []}, 200

        classes_teached = teacher_data.get('classes_teached', {})
        subjects_for_class = []

        # Check if the class exists in classes_teached
        if class_id in classes_teached:
            # Get all sections for this class
            sections = classes_teached[class_id].get('sections', {})

            # Collect all subject IDs across all sections
            subject_ids = []
            for section, section_subjects in sections.items():
                subject_ids.extend(section_subjects)

            # Remove duplicates
            subject_ids = list(set(subject_ids))

            # Get subject details for each subject ID
            for subject_id in subject_ids:
                subject_name = get_subject_name(subject_id)
                subjects_for_class.append({
                    'id': subject_id,
                    'name': subject_name
                })

        return {'subjects': subjects_for_class}, 200
    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/questions', methods=['GET'])
@login_required(user_types=['teacher'])
def get_questions():
    subject_id = request.args.get('subject')
    class_id = int(request.args.get('class'))
    if not subject_id or not class_id:
        return {'error': 'Subject ID and Class ID are required'}, 400

    try:
        questions_ref = database.child('questions')
        all_questions = questions_ref.get()
        questions_list = []

        if all_questions:
            for q_id, q_data in all_questions.items():
                if q_data.get('subject_id') == subject_id and q_data.get('class') == class_id:
                    questions_list.append({
                        'id': q_id,
                        'text': q_data.get('text', ''),
                        'subject_id': subject_id,
                        'question_type': q_data.get('question_type', 'mcq'),
                        'difficulty': q_data.get('difficulty', 'medium'),
                        'created_by_name': q_data.get('created_by_name', 'Unknown Teacher'),
                        'created_at': q_data.get('created_at', datetime.now().strftime('%Y-%m-%d')),
                        'marks': q_data.get('marks', 1),
                        'options': q_data.get('options', {}),
                        'column_a': q_data.get('column_a', {}),
                        'column_b': q_data.get('column_b', {}),
                        'assertion': q_data.get('assertion', ''),
                        'reason': q_data.get('reason', ''),
                        'case_text': q_data.get('case_text', '')
                    })

        return {'questions': questions_list}
    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/manage_students')
@login_required(user_types=['teacher'])
def manage_students():
    return render_template('teacher/manage_students.html')


@teacher_bp.route('/api/exams_and_students', methods=['GET'])
@login_required(user_types=['teacher'])
def get_exams_and_students():
    try:
        teacher_email = session.get('user_id')
        if not teacher_email:
            return {'error': 'User not authenticated'}, 401

        # Get teacher's data and exams
        teacher_data = get_teacher_data(teacher_email)
        teacher_exams = get_teacher_exams(teacher_email)

        # Get student data for classes taught by this teacher
        class_section_pairs = get_class_section_pairs(teacher_data)
        student_data = get_students_by_class_section(class_section_pairs)

        return jsonify({
            'exams': teacher_exams,
            'students': student_data
        })

    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/update_student_status', methods=['POST'])
@login_required(user_types=['teacher'])
def api_update_student_status():
    try:
        data = request.json
        student_email = data.get('student_email')
        new_status = data.get('status')

        if not student_email or new_status is None:
            return {'error': 'Missing required fields'}, 400

        name = update_student_status(student_email, new_status)

        return jsonify({
            'success': True,
            'message': f"Student {name} status updated to {new_status}"
        })

    except ValueError as e:
        return {'error': str(e)}, 404
    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/update_bulk_status', methods=['POST'])
@login_required(user_types=['teacher'])
def api_update_bulk_status():
    try:
        data = request.json
        student_emails = data.get('student_emails', [])
        new_status = data.get('status')

        if not student_emails or new_status is None:
            return {'error': 'Missing required fields'}, 400

        updated_count = update_bulk_student_status(student_emails, new_status)

        return jsonify({
            'success': True,
            'message': f"Updated status to {new_status} for {updated_count} students"
        })

    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/add_submission_reason', methods=['POST'])
@login_required(user_types=['teacher'])
def add_submission_reason():
    try:
        data = request.json
        student_email = data.get('student_email')
        exam_id = data.get('exam_id')
        reason = data.get('reason')

        if not student_email or not exam_id or not reason:
            return {'error': 'Missing required fields'}, 400

        manage_submission(student_email, exam_id, reason)

        return jsonify({
            'success': True,
            'message': "Submission reason added for student"
        })

    except ValueError as e:
        return {'error': str(e)}, 404
    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/delete_submission', methods=['POST'])
@login_required(user_types=['teacher'])
def delete_submission():
    try:
        data = request.json
        student_email = data.get('student_email')
        exam_id = data.get('exam_id')

        if not student_email or not exam_id:
            return {'error': 'Missing required fields'}, 400

        success = manage_submission(student_email, exam_id, delete=True)

        if success:
            return jsonify({
                'success': True,
                'message': "Submission deleted successfully"
            })
        else:
            return jsonify({
                'success': False,
                'message': "No submission found for this student"
            })

    except ValueError as e:
        return {'error': str(e)}, 404
    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/toggle_exam_status', methods=['POST'])
@login_required(user_types=['teacher'])
def toggle_exam_status():
    try:
        data = request.json
        exam_id = data.get('exam_id')
        new_status = data.get('status')

        if exam_id is None or new_status is None:
            return {'error': 'Missing required fields'}, 400

        update_exam_status(exam_id, new_status)

        return jsonify({
            'success': True,
            'message': f"Exam status updated to {'enabled' if new_status else 'disabled'}"
        })

    except ValueError as e:
        return {'error': str(e)}, 403 if "Unauthorized" in str(e) else 404
    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/total_questions_by_teacher', methods=['GET'])
@login_required(user_types=['teacher'])
def questions_by_teacher():
    try:
        teacher_email = session.get('user_id')
        if not teacher_email:
            return {'error': 'User not authenticated'}, 401

        teacher_data = get_teacher_data(teacher_email)
        questions_total = teacher_data.get('questions_created', 0)

        return jsonify({'questions_created': questions_total})
    except Exception as e:
        return {'error': str(e)}, 500


@teacher_bp.route('/api/recent_activity', methods=['GET'])
@login_required(user_types=['teacher'])
def get_recent_activity():
    try:
        teacher_email = session.get('user_id')
        teacher_exams = get_teacher_exams(teacher_email)
        activity_items = []

        for exam_data in teacher_exams:
            # Calculate submissions percentage if any
            submissions = exam_data.get('submissions', {})
            submission_count = len(submissions) - (1 if ' ' in submissions else 0)  # Subtract empty entry

            activity_items.append({
                'type': 'exam_created',
                'title': f"{exam_data.get('title')}",
                'description': f"Created for Class {exam_data.get('class')} - {exam_data.get('subject_name')}",
                'status': 'Active' if exam_data.get('exam_status') else 'Inactive',
                'status_class': 'success' if exam_data.get('exam_status') else 'warning',
                'timestamp': exam_data.get('created_at'),
                'submission_count': submission_count
            })

        # Sort activities by timestamp (newest first)
        activity_items.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'), reverse=True)

        # Limit to most recent 5 activities
        return jsonify({'activities': activity_items[:5]})

    except Exception as e:
        flash(f"Error in recent activity: {str(e)}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/api/class_performance', methods=['GET'])
@login_required(user_types=['teacher'])
def get_class_performance():
    try:
        teacher_email = session.get('user_id')
        teacher_data = get_teacher_data(teacher_email)
        classes_teached = get_teacher_classes(teacher_data)

        if not classes_teached:
            return jsonify({'class_performance': []})

        class_performance = []
        teacher_exams = get_teacher_exams(teacher_email)

        # Track submissions by class
        class_submissions = {}
        class_total_students = {}

        # First, calculate how many students are in each class
        for class_id, class_data in classes_teached.items():
            sections = class_data.get('sections', {})
            class_total_students[class_id] = 0

            # Count students in each section
            for section in sections:
                class_ref = database.child('classes').child(class_id).child(section).get()
                if class_ref:
                    # Subtract 1 for the null entry at index 0
                    student_count = len(class_ref) - 1 if isinstance(class_ref, list) else 0
                    class_total_students[class_id] += student_count

        # Then calculate submission rates for exams
        for exam_data in teacher_exams:
            exam_class = str(exam_data.get('class'))
            submissions = exam_data.get('submissions', {})

            # Remove the empty submission placeholder
            submission_count = len(submissions) - (1 if ' ' in submissions else 0)

            if exam_class not in class_submissions:
                class_submissions[exam_class] = {
                    'total_submissions': 0,
                    'expected_submissions': 0
                }

            class_submissions[exam_class]['total_submissions'] += submission_count

            # Expected submissions is the total students in that class
            expected = class_total_students.get(exam_class, 0)
            class_submissions[exam_class]['expected_submissions'] += expected

        # Calculate completion percentage for each class
        for class_id, data in class_submissions.items():
            if data['expected_submissions'] > 0:
                completion_percentage = (data['total_submissions'] / data['expected_submissions']) * 100

                # Determine color based on completion percentage
                color = 'success'
                if completion_percentage < 60:
                    color = 'warning'
                if completion_percentage < 40:
                    color = 'danger'

                class_performance.append({
                    'class': f"Class {class_id}",
                    'percentage': round(completion_percentage, 1),
                    'color': color
                })

        return jsonify({'class_performance': class_performance})

    except Exception as e:
        flash(f"Error in class performance: {str(e)}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/api/pending_submissions', methods=['GET'])
@login_required(user_types=['teacher'])
def get_pending_submissions():
    try:
        teacher_email = session.get('user_id')
        teacher_data = get_teacher_data(teacher_email)
        classes_teached = get_teacher_classes(teacher_data)

        if not classes_teached:
            return jsonify({'exam_submissions': {}})

        # Get all students in teacher's classes
        students_by_class = {}
        for class_id, class_data in classes_teached.items():
            sections = class_data.get('sections', {})
            students_by_class[class_id] = []
            for section in sections:
                # Get students in this section
                students_ref = database.child('students').get()
                if students_ref:
                    for email, student in students_ref.items():
                        if str(student.get('class')) == class_id and student.get('section') == section:
                            students_by_class[class_id].append({
                                'email': email.replace(',', '.'),  # Convert back from Firebase format
                                'name': student.get('name', 'Unknown Student'),
                                'roll_no': student.get('rollno', 'N/A')
                            })

        # Get active exams for each class taught by the teacher
        teacher_exams = get_teacher_exams(teacher_email)
        active_exams = []

        today = datetime.now().strftime('%Y-%m-%d')
        for exam_data in teacher_exams:
            if exam_data.get('exam_status'):
                exam_date = exam_data.get('exam_date')

                # Check if the exam is current or past due
                if exam_date and exam_date <= today:
                    active_exams.append({
                        'id': exam_data.get('id'),
                        'title': exam_data.get('title'),
                        'class': exam_data.get('class'),
                        'subject': exam_data.get('subject_name'),
                        'date': exam_date,
                        'submissions': exam_data.get('submissions', {})
                    })

        # Group pending submissions by exam
        exam_submissions = {}

        for exam in active_exams:
            exam_id = exam.get('id')
            exam_class = str(exam.get('class'))
            submissions = exam.get('submissions', {})

            submitted_emails = set()
            for key in submissions:
                submitted_emails.add(key.replace(',', '.'))

            # Find students who haven't submitted
            pending_students = []
            for student in students_by_class.get(exam_class, []):
                student_email = student.get('email')
                if student_email not in submitted_emails:
                    exam_date = datetime.strptime(exam.get('date'), '%Y-%m-%d')
                    days_overdue = (datetime.now() - exam_date).days

                    status = 'overdue' if days_overdue > 0 else 'due_soon' if days_overdue >= -2 else 'on_track'

                    pending_students.append({
                        'student_name': student.get('name'),
                        'student_email': student_email,
                        'days_overdue': days_overdue,
                        'status': status,
                        'initials': ''.join([name[0].upper() for name in student.get('name', 'US').split()[:2]])
                    })

            # Only add exams that have pending submissions
            if pending_students:
                # Sort students by days overdue (most overdue first)
                pending_students.sort(key=lambda x: x['days_overdue'], reverse=True)

                exam_submissions[exam_id] = {
                    'title': exam.get('title'),
                    'class': exam.get('class'),
                    'subject': exam.get('subject'),
                    'date': exam.get('date'),
                    'pending_students': pending_students
                }

        return jsonify({'exam_submissions': exam_submissions})

    except Exception as e:
        flash(f"Error in pending submissions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@teacher_bp.route('/api/dashboard_stats', methods=['GET'])
@login_required(user_types=['teacher'])
def get_dashboard_stats():
    try:
        teacher_email = session.get('user_id')
        teacher_data = get_teacher_data(teacher_email)

        if not teacher_data:
            return jsonify({'error': 'Teacher data not found'}), 404

        # Get classes taught by this teacher
        classes_teached = get_teacher_classes(teacher_data)

        # 1. Count total students
        total_students = get_total_students(classes_teached)

        # 2. Count active exams
        teacher_exams = get_teacher_exams(teacher_email)
        active_exams = sum(1 for exam in teacher_exams if exam.get('exam_status'))

        # 3. Count questions in question bank
        total_questions = teacher_data.get('questions_created', 0)

        # 4. Calculate average completion percentage
        avg_completion = calculate_completion_percentage(classes_teached, teacher_exams)

        return jsonify({
            'total_students': total_students,
            'active_exams': active_exams,
            'total_questions': total_questions,
            'avg_completion': avg_completion
        })

    except Exception as e:
        flash(f"Error in dashboard stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
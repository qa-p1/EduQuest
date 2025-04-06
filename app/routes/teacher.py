import time
from datetime import datetime
from flask import Blueprint, render_template, session, request, flash, jsonify
from app.utils.auth import login_required
from app.utils.database import database
from firebase_admin import db
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
            exams_ref = database.child('exams')
            new_exam_ref = exams_ref.push()

            exam_data = {
                'title': data.get('title'),
                'subject_id': data.get('subject_id'),
                'class': int(data.get('class')),
                'exam_type': data.get('exam_type'),
                'exam_date': data.get('exam_date'),
                'duration': data.get('duration'),
                'created_by': user_id,
                'created_by_name': user_name,
                'total_marks': data.get('total_marks', 0),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'questions': {},
                'exam_status': False
            }

            # Add questions to the exam
            for index, question in data.get('questions', {}).items():
                exam_data['questions'][index] = {
                    'question_id': question.get('question_id'),
                    'order': question.get('order'),
                    'marks': question.get('marks', 0)
                }

            new_exam_ref.set(exam_data)

            flash('Exam created successfully!', 'success')
            return jsonify({'success': True, 'exam_id': new_exam_ref.key})

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
        teacher_ref = database.child('administrators').child('teachers').child(user_email)
        teacher_data = teacher_ref.get()

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
                subject_data = database.child('subjects').child(subject_id).get()
                if subject_data:
                    subjects_for_class.append({
                        'id': subject_id,
                        'name': subject_data.get('name', 'Unknown Subject')
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

        # 1. Get teacher's classes and subjects
        teacher_ref = database.child('administrators').child('teachers').child(teacher_email)
        teacher_data = teacher_ref.get()

        if not teacher_data or 'classes_teached' not in teacher_data:
            return jsonify({'exams': [], 'students': {}})

        classes_teached = teacher_data.get('classes_teached', {})

        # 2. Get all exams created by this teacher
        exams_ref = database.child('exams')
        all_exams = exams_ref.get()

        teacher_exams = []
        if all_exams:
            for exam_id, exam_data in all_exams.items():
                if exam_data.get('created_by') == teacher_email:
                    # Get subject name
                    subject_name = "Unknown Subject"
                    subject_id = exam_data.get('subject_id')
                    if subject_id:
                        subject_data = database.child('subjects').child(subject_id).get()
                        if subject_data and 'name' in subject_data:
                            subject_name = subject_data['name']

                    # Add subject name to exam data
                    exam_data_with_id = dict(exam_data)
                    exam_data_with_id['id'] = exam_id
                    exam_data_with_id['subject_name'] = subject_name
                    teacher_exams.append(exam_data_with_id)

        # 3. Get students data for classes taught by this teacher
        student_data = {}
        class_section_pairs = []

        # Collect all class-section combinations taught by this teacher
        for class_id, class_data in classes_teached.items():
            sections = class_data.get('sections', {})
            for section, subject_ids in sections.items():
                class_section_pairs.append((class_id, section))

        # Get all students
        students_ref = database.child('students')
        all_students = students_ref.get()

        if all_students:
            for email, student in all_students.items():
                student_class = str(student.get('class'))
                student_section = student.get('section')

                # Check if this student belongs to one of the teacher's classes
                if (student_class, student_section) in class_section_pairs:
                    # Include only relevant students
                    student_data[email] = student

        return jsonify({
            'exams': teacher_exams,
            'students': student_data
        })

    except Exception as e:
        return {'error': str(e)}, 500


# In update_student_status route
@teacher_bp.route('/api/update_student_status', methods=['POST'])
@login_required(user_types=['teacher'])
def update_student_status():
    try:
        data = request.json
        student_email = data.get('student_email')
        new_status = data.get('status')

        if not student_email or not new_status:
            return {'error': 'Missing required fields'}, 400

        # Update the student status - safely encode email for Firebase
        safe_email = student_email.replace('.', ',')  # Replace dots with commas for Firebase
        student_ref = database.child('students').child(safe_email)
        current_student = student_ref.get()

        if not current_student:
            return {'error': 'Student not found'}, 404

        # Update only the status field
        student_ref.update({'status': new_status})

        return jsonify({
            'success': True,
            'message': f"Student {current_student.get('name', student_email)} status updated to {new_status}"
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Add detailed error logging
        return {'error': str(e)}, 500


# Similarly in update_bulk_status route
@teacher_bp.route('/api/update_bulk_status', methods=['POST'])
@login_required(user_types=['teacher'])
def update_bulk_status():
    try:
        data = request.json
        student_emails = data.get('student_emails', [])
        new_status = data.get('status')

        if not student_emails or not new_status:
            return {'error': 'Missing required fields'}, 400

        # Update multiple students at once
        updated_count = 0
        for email in student_emails:
            safe_email = email.replace('.', ',')  # Replace dots with commas for Firebase
            student_ref = database.child('students').child(safe_email)
            current_student = student_ref.get()

            if current_student:
                student_ref.update({'status': new_status})
                updated_count += 1

        return jsonify({
            'success': True,
            'message': f"Updated status to {new_status} for {updated_count} students"
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Add detailed error logging
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

        # Replace dots with commas for Firebase compatible key
        safe_email = student_email.replace('.', ',')

        # Create or update the submission record with reason
        exam_ref = database.child('exams').child(exam_id)
        current_exam = exam_ref.get()

        if not current_exam:
            return {'error': 'Exam not found'}, 404

        # Update or create the submissions object
        submissions = current_exam.get('submissions', {})
        submissions[safe_email] = {
            'reason': reason,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Update the exam with the new submissions data
        exam_ref.update({'submissions': submissions})

        return jsonify({
            'success': True,
            'message': f"Submission reason added for student"
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
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

        # Replace dots with commas for Firebase compatible key
        safe_email = student_email.replace('.', ',')

        # Get the exam data
        exam_ref = database.child('exams').child(exam_id)
        current_exam = exam_ref.get()

        if not current_exam:
            return {'error': 'Exam not found'}, 404

        # Get submissions and remove the specific student
        submissions = current_exam.get('submissions', {})

        if safe_email in submissions:
            del submissions[safe_email]

            # Update the exam with the modified submissions data
            exam_ref.update({'submissions': submissions})

            return jsonify({
                'success': True,
                'message': f"Submission deleted successfully"
            })
        else:
            return jsonify({
                'success': False,
                'message': f"No submission found for this student"
            })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
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

        # Update the exam status
        exam_ref = database.child('exams').child(exam_id)
        current_exam = exam_ref.get()

        if not current_exam:
            return {'error': 'Exam not found'}, 404

        # Make sure only the teacher who created the exam can toggle its status
        if current_exam.get('created_by') != session.get('user_id'):
            return {'error': 'Unauthorized to modify this exam'}, 403

        # Update only the exam_status field
        exam_ref.update({'exam_status': new_status})

        return jsonify({
            'success': True,
            'message': f"Exam status updated to {'enabled' if new_status else 'disabled'}"
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {'error': str(e)}, 500

@teacher_bp.route('/api/total_questions_by_teacher', methods=['GET'])
@login_required(user_types=['teacher'])
def questions_by_teacher():
    try:
        teacher_email = session.get('user_id')
        print(teacher_email)
        if not teacher_email:
            return {'error': 'User not authenticated'}, 401
        questions_total = database.child('administrators').child('teachers').child(teacher_email).child('questions_created').get()
        return jsonify({'questions_created': questions_total})
    except Exception as e:
        return {'error': str(e)}, 500
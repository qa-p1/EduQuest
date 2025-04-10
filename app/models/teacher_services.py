from datetime import datetime
from firebase_admin import db
from app.utils.database import database
from flask import session, flash


# Teacher data operations
def get_teacher_data(teacher_email=None):
    """Get teacher data with classes and sections taught"""
    if not teacher_email:
        teacher_email = session.get('user_id')

    teacher_ref = database.child('administrators').child('teachers').child(teacher_email)
    return teacher_ref.get()


def get_teacher_classes(teacher_data=None):
    """Extract classes_teached from teacher data"""
    if not teacher_data:
        teacher_data = get_teacher_data()

    return teacher_data.get('classes_teached', {}) if teacher_data else {}


# Exam operations
def create_exam(data, user_id, user_name):
    """Create a new exam in Firebase"""
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
        return new_exam_ref.key
    except Exception as e:
        flash(f"Error creating exam: {str(e)}")
        raise


def get_teacher_exams(teacher_email=None):
    """Get all exams created by this teacher with subject information"""
    if not teacher_email:
        teacher_email = session.get('user_id')

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

    return teacher_exams


def update_exam_status(exam_id, new_status, teacher_email=None):
    """Update exam status ensuring only owner can modify"""
    if not teacher_email:
        teacher_email = session.get('user_id')

    exam_ref = database.child('exams').child(exam_id)
    current_exam = exam_ref.get()

    if not current_exam:
        raise ValueError('Exam not found')

    if current_exam.get('created_by') != teacher_email:
        raise ValueError('Unauthorized to modify this exam')

    exam_ref.update({'exam_status': new_status})
    return True


# Student operations
def get_students_by_class_section(class_section_pairs):
    """Get students that belong to specific class-section pairs"""
    student_data = {}
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

    return student_data


def get_class_section_pairs(teacher_data=None):
    """Extract all class-section combinations taught by a teacher"""
    classes_teached = get_teacher_classes(teacher_data)
    class_section_pairs = []

    for class_id, class_data in classes_teached.items():
        sections = class_data.get('sections', {})
        for section in sections:
            class_section_pairs.append((class_id, section))

    return class_section_pairs


def update_student_status(student_email, new_status):
    """Update a student's status in Firebase"""
    safe_email = student_email.replace('.', ',')  # Replace dots with commas for Firebase
    student_ref = database.child('students').child(safe_email)
    current_student = student_ref.get()

    if not current_student:
        raise ValueError('Student not found')

    student_ref.update({'status': new_status})
    return current_student.get('name', student_email)


def update_bulk_student_status(student_emails, new_status):
    """Update multiple students' status at once"""
    updated_count = 0
    for email in student_emails:
        try:
            update_student_status(email, new_status)
            updated_count += 1
        except ValueError:
            # Skip if student not found
            continue

    return updated_count


# Submission operations
def manage_submission(student_email, exam_id, reason=None, delete=False):
    """Add or delete a submission reason for a student"""
    # Replace dots with commas for Firebase compatible key
    safe_email = student_email.replace('.', ',')

    # Get the exam data
    exam_ref = database.child('exams').child(exam_id)
    current_exam = exam_ref.get()

    if not current_exam:
        raise ValueError('Exam not found')

    # Get submissions
    submissions = current_exam.get('submissions', {})

    if delete:
        # Delete submission
        if safe_email in submissions:
            del submissions[safe_email]
            exam_ref.update({'submissions': submissions})
            return True
        return False
    else:
        # Add submission with reason
        submissions[safe_email] = {
            'reason': reason,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        exam_ref.update({'submissions': submissions})
        return True


# Dashboard statistics
def get_total_students(classes_teached):
    """Count total students across all classes taught by teacher"""
    total_students = 0
    for class_id, class_data in classes_teached.items():
        sections = class_data.get('sections', {})
        for section in sections:
            class_ref = database.child('classes').child(class_id).child(section).get()
            if class_ref:
                # Subtract 1 for the null entry at index 0
                student_count = len(class_ref) - 1 if isinstance(class_ref, list) else 0
                total_students += student_count
    return total_students


def get_subject_name(subject_id):
    """Get subject name by ID"""
    if subject_id:
        subject_data = database.child('subjects').child(subject_id).get()
        if subject_data:
            return subject_data.get('name', 'Unknown Subject')
    return "Unknown Subject"


def calculate_completion_percentage(classes_teached, exams):
    """Calculate completion percentage for teacher's exams"""
    total_submissions = 0
    total_expected = 0

    for exam_data in exams:
        exam_class = exam_data.get('class')
        submissions = exam_data.get('submissions', {})

        # Remove the empty submission placeholder
        submission_count = len(submissions) - (1 if ' ' in submissions else 0)
        total_submissions += submission_count

        # Count expected submissions for this exam
        expected = 0
        sections = classes_teached.get(str(exam_class), {}).get('sections', {})
        for section in sections:
            class_ref = database.child('classes').child(str(exam_class)).child(section).get()
            if class_ref:
                # Subtract 1 for the null entry at index 0
                student_count = len(class_ref) - 1 if isinstance(class_ref, list) else 0
                expected += student_count

        total_expected += expected

    # Calculate average completion percentage
    return round((total_submissions / total_expected * 100)) if total_expected > 0 else 0
from app.utils.database import database
from flask import session


def get_student_exams(student_id, student_class, student_section):
    """Get all exams available for the student"""
    exams_data = []
    try:
        # Get all exams
        exams_ref = database.child('exams')
        all_exams = exams_ref.get()

        # Get all teachers to check their assigned classes/sections
        teachers_ref = database.child('administrators/teachers')
        all_teachers = teachers_ref.get() or {}

        if all_exams:
            for exam_id, exam in all_exams.items():
                # Check if exam is for the student's class
                if exam.get('class') == student_class:
                    # Check if exam creator teaches the student's section
                    teacher_id = exam.get('created_by', '').replace('.', ',')
                    teacher_data = all_teachers.get(teacher_id, {})

                    # Check if the teacher teaches this student's section
                    teaches_section = False
                    classes_taught = teacher_data.get('classes_teached', {})

                    # Check if teacher teaches this class and section
                    if str(student_class) in classes_taught:
                        sections = classes_taught[str(student_class)].get('sections', {})
                        if student_section in sections:
                            teaches_section = True

                    if teaches_section:
                        # Check if student already submitted this exam
                        submitted = False
                        submissions = exam.get('submissions', {})
                        if student_id.replace('.', ',') in submissions:
                            submitted = True

                        # Add to exams list with submission status
                        exams_data.append({
                            'id': exam_id,
                            'title': exam.get('title', 'Untitled Exam'),
                            'subject_id': exam.get('subject_id', ''),
                            'exam_date': exam.get('exam_date', ''),
                            'duration': exam.get('duration', 60),
                            'exam_status': exam.get('exam_status', False),
                            'created_by_name': exam.get('created_by_name', 'Unknown'),
                            'submitted': submitted
                        })
    except Exception as e:
        print(f"Error fetching student exams: {e}")

    return exams_data


def get_exam_by_id(exam_id):
    """Get exam details by ID"""
    try:
        exam_ref = database.child('exams').child(exam_id)
        exam_data = exam_ref.get()
        return exam_data
    except Exception as e:
        print(f"Error fetching exam: {e}")
        return None


def check_submission_exists(exam_id, student_id):
    """Check if student has already submitted this exam"""
    student_key = student_id.replace('.', ',')
    try:
        submissions = database.child('exams').child(exam_id).child('submissions').child(student_key).get()
        return submissions is not None and submissions != ""
    except Exception as e:
        print(f"Error checking submission: {e}")
        return False


def save_exam_submission(exam_id, student_id, submission_id, submission_data):
    """Save student's exam submission"""
    student_key = student_id.replace('.', ',')
    try:
        # Save to students submissions
        student_sub_ref = database.child('students').child(student_key).child('submissions').child(submission_id)
        student_sub_ref.set(submission_data)

        # Save reference in exam submissions
        exam_sub_ref = database.child('exams').child(exam_id).child('submissions').child(student_key)
        exam_sub_ref.set(submission_id)

        return True
    except Exception as e:
        print(f"Error saving submission: {e}")
        return False
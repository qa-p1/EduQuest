from app.utils.database import database
from datetime import datetime
from app.models.subject import get_all_subjects
from flask import session

def get_teacher_questions(teacher_id):
    subjects = session['subjects']
    teacher_questions = []
    subject_names = {subject["id"]: subject["name"] for subject in subjects}
    try:
        questions_ref = database.child('questions')
        all_questions = questions_ref.get()
        if all_questions:
            for q_id, q_data in all_questions.items():
                if q_data.get('created_by') == teacher_id:
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
        print(f"Error fetching questions: {e}")

    return teacher_questions


def get_admin_questions(filters=None, page=1, items_per_page=10):
    filtered_questions = []
    total_pages = 1
    try:
        # Set defaults if filters not provided
        if filters is None:
            filters = {}

        subject_filter = filters.get('subject_filter', '')
        difficulty_filter = filters.get('difficulty_filter', '')
        created_by_filter = filters.get('created_by_filter', '')
        question_type_filter = filters.get('question_type_filter', '')

        # Get all questions from database
        questions_ref = database.child('questions')
        all_questions = questions_ref.get()

        if all_questions:
            # Get all users for creator name lookup
            all_teachers = database.child('administrators/teachers').get() or {}
            all_admins = database.child('administrators/admins').get() or {}
            all_students = database.child('students').get() or {}

            # Get all subjects for subject name lookup
            subjects = get_all_subjects()
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

        # Calculate pagination
        total_items = len(filtered_questions)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1

        # Ensure page is within valid range
        page = max(1, min(page, total_pages))

        # Get questions for current page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        paginated_questions = filtered_questions[start_idx:end_idx]

        return {
            'questions': paginated_questions,
            'total_pages': total_pages,
            'current_page': page,
            'total_items': total_items
        }

    except Exception as e:
        print(f"Error fetching admin questions: {e}")
        return {
            'questions': [],
            'total_pages': 1,
            'current_page': 1,
            'total_items': 0
        }


def get_question_by_id(question_id):
    try:
        question_ref = database.child(f'questions/{question_id}')
        return question_ref.get()
    except Exception as e:
        print(f"Error fetching question: {e}")
        return None


def add_question(question_data):
    try:
        questions_ref = database.child('questions')
        new_question_ref = questions_ref.push()
        new_question_ref.set(question_data)
        return True
    except Exception as e:
        print(f"Error adding question: {e}")
        return False


def update_question(question_id, updated_data):
    try:
        question_ref = database.child(f'questions/{question_id}')
        question_ref.update(updated_data)
        return True
    except Exception as e:
        print(f"Error updating question: {e}")
        return False


def delete_question(question_id):
    """Delete a question"""
    try:
        question_ref = database.child(f'questions/{question_id}')
        question_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting question: {e}")
        return False

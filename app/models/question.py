from app.utils.database import database
from app.models.subject import get_all_subjects
from flask import session, request, flash


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


# New helper functions for processing different question types
def get_base_question_data(form_data, user_id, user_type):
    """Extract and validate basic question data from form."""
    subject_id = form_data.get('subject')
    question_type = form_data.get('question_type', 'mcq')
    difficulty = form_data.get('difficulty')
    class_of_question = form_data.get('class', '')
    marks_of_question = form_data.get('marks_for_ques')

    if not all([subject_id, question_type, difficulty]):
        return None, "Basic question information is required."

    # Base question data
    question_data = {
        "subject_id": subject_id,
        "question_type": question_type,
        "difficulty": difficulty,
        "class": int(class_of_question) if class_of_question and class_of_question.isdigit() else '',
        "created_by": user_id,
        "created_by_type": user_type,
        "marks": int(marks_of_question)
    }

    return question_data, None


def process_mcq_data(form_data, existing_data=None):
    """Process and validate MCQ question data."""
    question_text = form_data.get('question_text')
    option1 = form_data.get('option1')
    option2 = form_data.get('option2')
    option3 = form_data.get('option3')
    option4 = form_data.get('option4')
    correct_answer = form_data.get('correct_answer')

    if not all([question_text, option1, option2, option3, option4, correct_answer]):
        return None, "All fields for MCQ are required."

    # Use the existing structure for options (dict or list) if updating
    options_data = {
        "0": option1,
        "1": option2,
        "2": option3,
        "3": option4
    }

    if existing_data and isinstance(existing_data.get('options'), list):
        options_data = [option1, option2, option3, option4]

    question_data = {
        "text": question_text,
        "options": options_data,
        "correct_answer": int(correct_answer) - 1,
    }

    return question_data, None


def process_fill_in_blanks_data(form_data):
    """Process and validate Fill in the Blanks question data."""
    question_text = form_data.get('fitb_text')

    # Get all blanks from form
    blanks = []
    i = 1
    while True:
        blank = form_data.get(f'blank{i}')
        if blank is None:
            break
        blanks.append(blank)
        i += 1

    if not question_text or not blanks:
        return None, "Question text and at least one blank are required."

    question_data = {
        "text": question_text,
        "blanks": blanks
    }

    return question_data, None


def process_match_columns_data(form_data, existing_data=None):
    """Process and validate Match Columns question data."""
    # Get column items from form
    column_a = {}
    column_b = {}
    matches = {}

    # For updating, check if existing data uses lists or dicts
    use_lists = existing_data and (
            isinstance(existing_data.get('column_a'), list) or
            isinstance(existing_data.get('column_b'), list)
    )

    if use_lists:
        column_a = []
        column_b = []
        matches = []

    i = 1
    valid_items = 0  # Counter for valid items

    while True:
        item_a = form_data.get(f'column_a_{i}')
        item_b = form_data.get(f'column_b_{i}')

        if item_a is None or item_b is None:
            break

        # Only add if both items have content
        if item_a.strip() and item_b.strip():
            if use_lists:
                column_a.append(item_a)
                column_b.append(item_b)
                matches.append(str(valid_items))  # Use valid_items counter for list indexes
            else:
                column_a[str(valid_items)] = item_a  # Use valid_items counter starting from 0
                column_b[str(valid_items)] = item_b
                matches[str(valid_items)] = str(valid_items)

            valid_items += 1

        i += 1

    if valid_items == 0:
        return None, "At least one pair of matching items is required."

    question_data = {
        "text": "Match the following items:",
        "column_a": column_a,
        "column_b": column_b,
        "matches": matches
    }

    return question_data, None


def process_assertion_reason_data(form_data):
    """Process and validate Assertion-Reason question data."""
    assertion = form_data.get('assertion')
    reason = form_data.get('reason')
    ar_correct_option = form_data.get('ar_correct_option')

    if not assertion or not reason or not ar_correct_option:
        return None, "Assertion, reason, and correct option are required."

    question_data = {
        "text": "Assertion and Reason Question",
        "assertion": assertion,
        "reason": reason,
        "ar_correct_option": ar_correct_option
    }

    return question_data, None


def process_case_based_data(form_data, existing_data=None):
    """Process and validate Case-Based question data."""
    case_content = form_data.get('case_content')

    if not case_content:
        return None, "Case content is required."

    # Process sub-questions for the case
    case_questions = []
    i = 1
    while True:
        sub_question = form_data.get(f'case_question_{i}')
        if not sub_question:
            break

        # Get options for this sub-question
        options = {}
        options_list = []

        for j in range(0, 4):
            option = form_data.get(f'case_q{i}_option{j}')
            if option:
                options[str(j)] = option
                options_list.append(option)

        correct_answer = form_data.get(f'case_q{i}_correct')

        # Determine structure (dict or list) for options based on existing data
        if existing_data and existing_data.get('case_questions'):
            existing_case_q = existing_data.get('case_questions', [{}])[0]
            uses_dict = isinstance(existing_case_q.get('options'), dict)
        else:
            uses_dict = True  # Default to dict for new questions

        if sub_question and correct_answer:
            if uses_dict and options:
                case_questions.append({
                    'text': sub_question,
                    'options': options,
                    'correct_answer': correct_answer
                })
            elif not uses_dict and options_list:
                case_questions.append({
                    'text': sub_question,
                    'options': options_list,
                    'correct_answer': correct_answer
                })

        i += 1

    if not case_questions:
        return None, "At least one case-based question is required."

    question_data = {
        "text": "Case-based Questions",
        "case_content": case_content,
        "case_questions": case_questions
    }

    return question_data, None


def process_question_data(form_data, user_id, user_type, existing_data=None):
    """
    Process form data for any question type.
    Returns (question_data, error_message)
    If error_message is not None, question_data will be None
    """
    # Get base question data
    base_data, error = get_base_question_data(form_data, user_id, user_type)
    if error:
        return None, error

    # Get question type
    question_type = base_data.get("question_type")

    # Process type-specific data
    type_specific_data = None
    error = None

    if question_type == 'mcq':
        type_specific_data, error = process_mcq_data(form_data, existing_data)
    elif question_type == 'fill_in_blanks':
        type_specific_data, error = process_fill_in_blanks_data(form_data)
    elif question_type == 'match_columns':
        type_specific_data, error = process_match_columns_data(form_data, existing_data)
    elif question_type == 'assertion_reason':
        type_specific_data, error = process_assertion_reason_data(form_data)
    elif question_type == 'case_based':
        type_specific_data, error = process_case_based_data(form_data, existing_data)
    else:
        return None, f"Unsupported question type: {question_type}"

    if error:
        return None, error

    # Merge base data with type-specific data
    question_data = {**base_data, **type_specific_data}
    return question_data, None
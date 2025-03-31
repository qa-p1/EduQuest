from app.utils.database import database


def get_all_subjects(teacher=None):
    subjects = []
    subjects_ref = database.child('subjects')
    subjects_data = subjects_ref.get()
    if teacher:
        for key, value in subjects_data.items():
            if teacher_teaches_subject(teacher, key):
                subjects.append({"id": key, "name": value.get("name", "Unknown")})
    else:
        for key1, value1 in subjects_data.items():
            subjects.append({"id": key1, "name": value1.get("name", "Unknown")})
    return subjects


def add_new_subject(subject_name):
    try:
        subjects_ref = database.child('subjects')
        new_subject_ref = subjects_ref.push()
        new_subject_ref.set({"name": subject_name})
        return True
    except Exception as e:
        print(f"Error adding subject: {e}")
        return False


def update_subject_name(subject_id, new_name):
    try:
        subject_ref = database.child(f'subjects/{subject_id}')
        subject_ref.update({"name": new_name})
        return True
    except Exception as e:
        print(f"Error updating subject: {e}")
        return False


def delete_subject(subject_id):
    try:
        subject_ref = database.child(f'subjects/{subject_id}')
        subject_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting subject: {e}")
        return False


def teacher_teaches_subject(teacher_id, subject_id):
    try:
        teacher_ref = database.child(f'administrators/teachers/{teacher_id}')
        teacher_data = teacher_ref.get()
        if not teacher_data or 'subjects' not in teacher_data:
            return False
        subject_ref = database.child(f'subjects/{subject_id}')
        subject_data = subject_ref.get()

        if not subject_data or 'name' not in subject_data:
            return False

        subject_name = subject_data.get('name').lower()
        teacher_subjects = [s.lower() for s in teacher_data.get('subjects', [])]
        return subject_name in teacher_subjects

    except Exception as e:
        print(f"Error checking teacher subjects: {e}")
        return False

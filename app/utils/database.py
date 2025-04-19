from firebase_admin import db
from flask import flash, redirect, url_for
import datetime
from app.utils.auth import hash_password

database = db.reference('/')


def get_user_data(user_type, user_id):
    if user_type == 'student':
        ref = database.child(f'students/{user_id}')
    elif user_type == 'teacher':
        ref = database.child(f'administrators/teachers/{user_id}')
    elif user_type == 'admin':
        ref = database.child(f'administrators/admins/{user_id}')
    else:
        flash("Invalid user type.", 'danger')
        # Consider raising an exception or returning None instead of redirecting here
        return None # Modified to avoid direct redirect

    return ref.get()


def update_teacher_name(teacher_id, new_name):
    # This function seems specific, consider using the more general update_teacher_data
    print("Warning: update_teacher_name is specific, consider using update_teacher_data")
    try:
        database.child(f'administrators/teachers/{teacher_id}').update({
            'name': new_name
        })
        return True
    except Exception as e:
        print(f"Error updating teacher name: {str(e)}")
        return False


def update_teacher_password(teacher_id, hashed_password):
    # This function is also specific, update_teacher_data handles password updates
    print("Warning: update_teacher_password is specific, consider using update_teacher_data")
    try:
        database.child(f'administrators/teachers/{teacher_id}').update({
            'password': hashed_password
        })
        return True
    except Exception as e:
        print(f"Error updating teacher password: {str(e)}")
        return False


def check_teacher_id_exists(teacher_id):
    """Check if a teacher ID already exists in the database."""
    try:
        ref = db.reference('administrators/teachers') # Corrected path
        # Query teachers with the given ID
        # Firebase Realtime DB filtering works best on exact matches or ranges,
        # but iterating might be necessary if not indexed properly.
        # For efficiency, ensure 'tchid' is indexed in Firebase rules if dataset is large.
        teachers = ref.order_by_child('tchid').equal_to(int(teacher_id)).get() # Ensure tchid is stored as int
        return bool(teachers)  # Return True if any match found
    except Exception as e:
        print(f"Error checking teacher ID: {e}")
        return True # Default to True on error to prevent accidental duplicates if check fails


def get_all_subjects():
    """Fetches all subjects from the Realtime Database."""
    try:
        ref = db.reference('subjects')
        subjects = ref.get()
        return subjects if subjects else {}
    except Exception as e:
        print(f"Error fetching subjects: {e}")
        return {}


def check_email_exists(email, exclude_uid=None):
    """Checks if an email exists, optionally excluding a specific user UID (for updates)."""
    try:
        teachers_ref = db.reference('administrators/teachers')
        snapshot = teachers_ref.order_by_child('email').equal_to(email).get()
        if not snapshot:
            return False # Email definitely doesn't exist

        # If we found matches, check if they belong to the user we are excluding
        if exclude_uid:
            for uid, data in snapshot.items():
                if uid != exclude_uid:
                    return True # Found the email associated with a DIFFERENT user
            return False # Email only exists for the user we are excluding
        else:
            return True # Email exists and we weren't excluding anyone
    except Exception as e:
        print(f"Error checking email existence: {e}")
        # Safer to assume it exists on error to prevent duplicates
        return True


def add_teacher_to_db(teacher_uid, teacher_data):
    try:
        # Add password hash
        if 'password' in teacher_data:
            hashed_password = hash_password(teacher_data['password'])
            teacher_data['password'] = hashed_password

        # Store teacher data in administrators/teachers/{uid}
        teachers_ref = db.reference('administrators/teachers')
        teachers_ref.child(teacher_uid).set(teacher_data)

    except Exception as e:
        raise Exception(f"Error saving teacher data to database: {e}")

# --- NEW FUNCTIONS ---
def get_all_teachers():
    """Fetches all teacher records from the Realtime Database."""
    try:
        ref = db.reference('administrators/teachers')
        teachers = ref.get()
        return teachers if teachers else {}
    except Exception as e:
        print(f"Error fetching all teachers: {e}")
        return {}

def get_teacher_by_uid(teacher_uid):
    """Fetches a specific teacher's data by their UID."""
    try:
        ref = db.reference(f'administrators/teachers/{teacher_uid}')
        teacher_data = ref.get()
        return teacher_data
    except Exception as e:
        print(f"Error fetching teacher by UID ({teacher_uid}): {e}")
        return None

def update_teacher_data(teacher_uid, updated_data):
    """Updates specific fields for a teacher in the database."""
    try:
        # Hash password if it's included in the update
        if 'password' in updated_data and updated_data['password']:
             hashed_password = hash_password(updated_data['password'])
             updated_data['password'] = hashed_password
        elif 'password' in updated_data:
             # Remove empty password field if present, so we don't overwrite existing hash
             del updated_data['password']

        ref = db.reference(f'administrators/teachers/{teacher_uid}')
        ref.update(updated_data)
        return True
    except Exception as e:
        print(f"Error updating teacher data for UID ({teacher_uid}): {e}")
        return False
# --- END OF NEW FUNCTIONS ---

def delete_firebase_auth_user(uid):
    """
    Deletes a teacher record from the Realtime Database.
    Note: This doesn't delete the user from Firebase Authentication itself,
          only the record in the Realtime Database path used by this app.
    """
    try:
        # Remove teacher record from administrators/teachers/{uid}
        teachers_ref = db.reference(f'administrators/teachers/{uid}')
        teachers_ref.delete()
        print(f"Deleted teacher data for UID: {uid} from RTDB")
        return True
    except Exception as e:
        print(f"Error deleting teacher data during rollback for UID ({uid}): {e}")
        return False
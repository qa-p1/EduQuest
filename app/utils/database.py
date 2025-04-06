from firebase_admin import db
from flask import flash, redirect, url_for
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
        return redirect(url_for('auth.logout'))

    return ref.get()
def update_teacher_name(teacher_id, new_name):
    """
    Update teacher's name in the database
    """
    try:
        database.child(f'administrators/teachers/{teacher_id}').update({
            'name': new_name
        })
        return True
    except Exception as e:
        print(f"Error updating teacher name: {str(e)}")
        return False

def update_teacher_password(teacher_id, hashed_password):
    """
    Update teacher's password in the database
    """
    try:
        database.child(f'administrators/teachers/{teacher_id}').update({
            'password': hashed_password
        })
        return True
    except Exception as e:
        print(f"Error updating teacher password: {str(e)}")
        return False
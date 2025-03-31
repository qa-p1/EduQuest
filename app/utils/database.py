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
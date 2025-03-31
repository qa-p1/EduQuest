from functools import wraps
from flask import session, redirect, url_for, flash
import re
import bcrypt


def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def check_password(stored_hash, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))


def login_required(user_types=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                target_user_type = user_types[0] if isinstance(user_types, list) and user_types else None
                flash("Please log in to access this page", 'danger')
                return redirect(url_for('auth.login', user_type=target_user_type))

            if user_types and session.get('user_type') not in user_types:
                flash(f"You don't have permission to access this page", 'danger')
                return redirect(url_for('common.dashboard'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator

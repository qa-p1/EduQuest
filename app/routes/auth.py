from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.auth import is_valid_email
from app.models.user import authenticate_user
from app.utils.menu import get_menu_items
from app.models.subject import get_all_subjects

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('common.dashboard'))

    user_type = request.args.get('user_type') or request.form.get('user_type')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not is_valid_email(email):
            flash("Please enter a valid email address.", 'warning')
            return render_template('login.html', user_type=user_type)
        try:
            user_data = authenticate_user(email, password, user_type)

            if user_data:
                session['user_id'] = user_data['user_id']
                session['email'] = email
                session['user_type'] = user_data['user_type']
                session['name'] = user_data['name']

                session['menu_items'] = get_menu_items(user_type)
                if user_data['user_type'] == 'teacher':
                    session['subjects'] = get_all_subjects(user_data['user_id'])
                else:
                    session['subjects'] = get_all_subjects()

                return redirect(url_for('common.dashboard'))

            flash("Invalid credentials. Please try again.", 'danger')

        except Exception as e:
            flash(f"Authentication error: {str(e)}", 'danger')
            flash(f"Login error: {str(e)}")

    return render_template('login.html', user_type=user_type)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", 'primary')
    return redirect(url_for('auth.index'))


@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('common.dashboard'))

    return render_template('index.html')
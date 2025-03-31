from flask import Blueprint, render_template, redirect, url_for, session, flash
from app.utils.auth import login_required
from app.utils.database import get_user_data

common_bp = Blueprint('common', __name__)


@common_bp.route('/dashboard')
@login_required()
def dashboard():
    user_type = session.get('user_type')
    if user_type == 'student':
        return redirect(url_for('student.dashboard'))
    elif user_type == 'teacher':
        return redirect(url_for('teacher.dashboard'))
    elif user_type == 'admin':
        return redirect(url_for('admin.dashboard'))
    session.clear()
    flash("Session error. Please log in again.", 'danger')
    return redirect(url_for('auth.login'))


@common_bp.route('/profile')
@login_required()
def profile():
    user_type = session.get('user_type')
    user_id = session.get('user_id')
    try:
        user_data = get_user_data(user_type, user_id)
        return render_template('profile.html', user_data=user_data)

    except Exception as e:
        flash(f"Error loading profile: {str(e)}", 'danger')
        return redirect(url_for('common.dashboard'))

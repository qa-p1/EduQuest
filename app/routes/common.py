from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from app.utils.auth import login_required
from app.utils.database import get_user_data, update_teacher_name, update_teacher_password
from app.utils.auth import check_password, hash_password

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


@common_bp.route('/profile', methods=['GET', 'POST'])
@login_required()
def profile():
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    try:
        user_data = get_user_data(user_type, user_id)

        if request.method == 'POST' and user_type == 'teacher':
            if 'update_name' in request.form:
                new_name = request.form.get('name')
                if new_name and new_name != user_data.get('name'):
                    update_teacher_name(user_id, new_name)
                    flash("Your name has been updated successfully!", 'success')
                    return redirect(url_for('common.profile'))

            elif 'change_password' in request.form:
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')

                if not current_password or not new_password or not confirm_password:
                    flash("All password fields are required!", 'danger')
                    return redirect(url_for('common.profile'))

                if new_password != confirm_password:
                    flash("New passwords do not match!", 'danger')
                    return redirect(url_for('common.profile'))

                if not check_password(user_data.get('password'), current_password):
                    flash("Current password is incorrect!", 'danger')
                    return redirect(url_for('common.profile'))

                hashed_password = hash_password(new_password)
                update_teacher_password(user_id, hashed_password)
                flash("Your password has been changed successfully!", 'success')
                return redirect(url_for('common.profile'))

        return render_template('profile.html', user_data=user_data)

    except Exception as e:
        flash(f"Error loading profile: {str(e)}", 'danger')
        return redirect(url_for('common.dashboard'))
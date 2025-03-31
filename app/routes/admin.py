from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.auth import login_required
from app.models.subject import add_new_subject, update_subject_name, delete_subject

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required(user_types=['admin'])
def dashboard():
    return render_template('admin/dashboard.html')


@admin_bp.route('/add_subject', methods=['GET', 'POST'])
@login_required(user_types=['admin'])
def add_subject():
    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        if subject_name:
            try:
                add_new_subject(subject_name)
                flash(f"Subject '{subject_name}' added successfully!", 'primary')
            except Exception as e:
                flash(f"Error adding subject: {e}", 'danger')

    return render_template('admin/add_subject.html', subjects=session['subjects'])


@admin_bp.route('/delete_subject/<subject_id>')
@login_required(user_types=['admin'])
def delete_subject(subject_id):
    try:
        delete_subject(subject_id)
        flash("Subject deleted successfully!", 'primary')
    except Exception as e:
        flash(f"Error deleting subject: {e}", 'danger')
    return redirect(url_for('admin.add_subject'))


@admin_bp.route('/update_subject/<subject_id>', methods=['POST'])
@login_required(user_types=['admin'])
def update_subject(subject_id):
    new_name = request.form.get('new_name')
    if new_name:
        try:
            update_subject_name(subject_id, new_name)
            flash("Subject updated successfully!", 'primary')
        except Exception as e:
            flash(f"Error updating subject: {e}", 'danger')
    return redirect(url_for('admin.add_subject'))

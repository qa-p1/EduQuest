from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify # Added jsonify
from app.utils.auth import login_required, hash_password # Added hash_password
from app.models.subject import add_new_subject, update_subject_name, delete_subject
import datetime
from app.utils.database import ( # Consolidated imports
    get_all_subjects, check_teacher_id_exists, check_email_exists,
    add_teacher_to_db, delete_firebase_auth_user,
    get_all_teachers, get_teacher_by_uid, update_teacher_data
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required(user_types=['admin'])
def dashboard():
    # You might want to fetch counts here later
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
                # Refresh subjects in session after adding
                session['subjects'] = get_all_subjects()
            except Exception as e:
                flash(f"Error adding subject: {e}", 'danger')
            # Redirect to GET to prevent form resubmission
            return redirect(url_for('admin.add_subject'))

    # Ensure subjects are fresh on GET request too
    if 'subjects' not in session:
         session['subjects'] = get_all_subjects()

    return render_template('admin/add_subject.html', subjects=session.get('subjects', {}))


@admin_bp.route('/delete_subject/<subject_id>')
@login_required(user_types=['admin'])
def delete_subject_route(subject_id): # Renamed function to avoid clash with import
    try:
        delete_subject(subject_id)
        # Refresh subjects in session after deleting
        session['subjects'] = get_all_subjects()
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
            # Refresh subjects in session after updating
            session['subjects'] = get_all_subjects()
            flash("Subject updated successfully!", 'primary')
        except Exception as e:
            flash(f"Error updating subject: {e}", 'danger')
    return redirect(url_for('admin.add_subject'))

# --- NEW ROUTE: Manage Teachers ---
@admin_bp.route('/manage_teachers')
@login_required(user_types=['admin'])
def manage_teachers():
    try:
        teachers = get_all_teachers()
        return render_template('admin/manage_teachers.html', teachers=teachers)
    except Exception as e:
        flash(f"Error loading teachers: {e}", 'danger')
        return render_template('admin/manage_teachers.html', teachers={})

# --- NEW ROUTE: Edit Teacher (GET and POST) ---
@admin_bp.route('/edit_teacher/<teacher_uid>', methods=['GET', 'POST'])
@login_required(user_types=['admin'])
def edit_teacher(teacher_uid):
    # Fetch teacher data once for both GET and POST validation
    teacher = get_teacher_by_uid(teacher_uid)
    if not teacher:
        flash('Teacher not found.', 'danger')
        return redirect(url_for('admin.manage_teachers'))

    # Make sure teacher data includes UID for the template/form action
    teacher['uid'] = teacher_uid

    if request.method == 'POST':
        # --- Form Data Extraction ---
        name = request.form.get('teacher_name')
        # Email and tchid are read-only, fetch from original data
        email = teacher.get('email')
        tchid = teacher.get('tchid')
        mobile = request.form.get('mobile_number')
        status = request.form.get('status')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # --- Validation ---
        if not all([name, mobile, status]):
            flash('Name, Mobile Number, and Status fields are required.', 'danger')
            # Re-render edit page with existing data and error
            subjects = get_all_subjects()
            return render_template('edit_teacher.html', teacher=teacher, subjects=subjects)

        if password or confirm_password: # Only validate password if user attempts to change it
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                subjects = get_all_subjects()
                return render_template('edit_teacher.html', teacher=teacher, subjects=subjects)
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                subjects = get_all_subjects()
                return render_template('edit_teacher.html', teacher=teacher, subjects=subjects)

        if not mobile.isdigit() or len(mobile) != 10:
            flash('Mobile number must be a 10-digit number.', 'danger')
            subjects = get_all_subjects()
            return render_template('edit_teacher.html', teacher=teacher, subjects=subjects)

        # --- Process Classes/Sections/Subjects ---
        classes_taught = {}
        class_count = int(request.form.get('class_count', 0))
        all_subject_ids_for_teacher = set() # Use a set for efficiency

        for i in range(1, class_count + 1):
            class_num = request.form.get(f'class_{i}')
            if not class_num: continue

            sections_data = {}
            # Find all section inputs for this class index
            section_inputs = [k for k in request.form.keys() if k.startswith(f'section_{i}_')]

            if not section_inputs: continue # Skip class if no sections defined

            for section_key in section_inputs:
                try:
                    # Extract section index j from section_i_j
                    section_index = section_key.split('_')[-1]
                    section_value = request.form.get(section_key, '').strip().lower()
                    subjects_key = f'subjects_{i}_{section_index}'
                    subject_ids_for_section = request.form.getlist(subjects_key)

                    if section_value and subject_ids_for_section:
                        sections_data[section_value] = subject_ids_for_section
                        all_subject_ids_for_teacher.update(subject_ids_for_section)
                except (IndexError, ValueError) as e:
                     print(f"Warning: Could not parse section/subject key: {section_key} - {e}")
                     continue # Skip malformed key

            if sections_data: # Only add class if it has valid sections
                 classes_taught[class_num] = {"sections": sections_data}

        if not classes_taught:
            flash('At least one complete class-section-subject assignment is required.', 'danger')
            subjects = get_all_subjects()
            return render_template('edit_teacher.html', teacher=teacher, subjects=subjects)

        # Get subject names from IDs for the 'subjects' array
        subjects_list = []
        all_subjects_db = get_all_subjects()
        for subj_id in all_subject_ids_for_teacher:
            if subj_id in all_subjects_db:
                subjects_list.append(all_subjects_db[subj_id]['name'])

        # --- Prepare Data for Update ---
        update_payload = {
            'name': name,
            'mobileno': int(mobile), # Store as integer if needed by other parts of app
            'status': status,
            'classes_teached': classes_taught,
            'subjects': sorted(list(set(subjects_list))) # Ensure unique and sorted names
        }

        # Only include password if a new one was provided
        if password:
            update_payload['password'] = password # Hashing happens in update_teacher_data

        try:
            if update_teacher_data(teacher_uid, update_payload):
                flash(f'Teacher "{name}" updated successfully!', 'success')
                return redirect(url_for('admin.manage_teachers'))
            else:
                flash('An error occurred while updating the teacher.', 'danger')
        except Exception as e:
            flash(f'Error updating teacher: {e}', 'danger')

        # If update fails, re-render the form with submitted (but potentially invalid) data for correction
        # We need to reconstruct the 'teacher' object partially with form data for pre-filling
        teacher.update({ # Update the dict to reflect submitted values for re-rendering
             'name': name,
             'mobileno': mobile, # Keep as string for form value
             'status': status,
             'classes_teached': classes_taught # Pass the structure for JS pre-population
        })
        subjects = get_all_subjects()
        return render_template('/edit_teacher.html', teacher=teacher, subjects=subjects)

    # --- GET Request Handling ---
    else:
        try:
            subjects = get_all_subjects()
            if not subjects:
                 flash('No subjects found in the system. Please add subjects.', 'warning')

            # Ensure classes_teached exists, even if empty, for the template JS
            if 'classes_teached' not in teacher:
                teacher['classes_teached'] = {}

            return render_template('/edit_teacher.html', teacher=teacher, subjects=subjects)
        except Exception as e:
            flash(f'Error loading data for edit form: {e}', 'danger')
            return redirect(url_for('admin.manage_teachers'))

@admin_bp.route('/add_teacher', methods=['GET', 'POST'])
@login_required(user_types=['admin'])
def add_teacher():
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        name = request.form.get('teacher_name')
        email = request.form.get('teacher_email')
        mobile = request.form.get('mobile_number')
        status = request.form.get('status')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # --- Basic Validation ---
        if not all([teacher_id, name, email, mobile, status, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.add_teacher'))
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('admin.add_teacher'))
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('admin.add_teacher'))
        if not mobile.isdigit() or len(mobile) != 10:
            flash('Mobile number must be a 10-digit number.', 'danger')
            return redirect(url_for('admin.add_teacher'))

        # --- Existence Checks ---
        # Use the updated check_email_exists (without exclude_uid)
        if check_email_exists(email):
            flash('Email address already in use.', 'danger')
            return redirect(url_for('admin.add_teacher'))

        if check_teacher_id_exists(teacher_id):
            flash('Teacher ID already in use.', 'danger')
            return redirect(url_for('admin.add_teacher'))

        # --- Process Classes/Sections/Subjects ---
        classes_taught = {}
        class_count = int(request.form.get('class_count', 0))
        all_subject_ids_for_teacher = set() # Use a set

        for i in range(1, class_count + 1):
            class_num = request.form.get(f'class_{i}')
            if not class_num: continue

            sections_data = {}
             # Find all section inputs for this class index
            section_inputs = [k for k in request.form.keys() if k.startswith(f'section_{i}_')]

            if not section_inputs: continue # Skip class if no sections defined

            for section_key in section_inputs:
                try:
                     # Extract section index j from section_i_j
                    section_index = section_key.split('_')[-1]
                    section_value = request.form.get(section_key, '').strip().lower()
                    subjects_key = f'subjects_{i}_{section_index}'
                    subject_ids_for_section = request.form.getlist(subjects_key)

                    if section_value and subject_ids_for_section:
                        sections_data[section_value] = subject_ids_for_section
                        all_subject_ids_for_teacher.update(subject_ids_for_section)
                except (IndexError, ValueError) as e:
                     print(f"Warning: Could not parse section/subject key: {section_key} - {e}")
                     continue # Skip malformed key

            if sections_data: # Only add class if it has valid sections
                 classes_taught[class_num] = {"sections": sections_data}


        if not classes_taught:
            flash('At least one complete class-section-subject assignment is required.', 'danger')
            return redirect(url_for('admin.add_teacher'))

        # Get subject names from IDs for the 'subjects' array
        subjects_list = []
        all_subjects_db = get_all_subjects()
        for subj_id in all_subject_ids_for_teacher:
            if subj_id in all_subjects_db:
                subjects_list.append(all_subjects_db[subj_id]['name'])

        # --- Prepare Teacher Data ---
        # Use email as UID (replace '.' with ',' - common Firebase key workaround)
        teacher_uid = email.replace('.', ',')

        teacher_data = {
            'uid': teacher_uid, # Store UID within the record too
            'tchid': int(teacher_id),
            'name': name,
            'email': email,
            'mobileno': int(mobile),
            'status': status,
            'classes_teached': classes_taught,
            'subjects': sorted(list(set(subjects_list))), # Ensure unique and sorted names
            'password': password, # Hashing done in add_teacher_to_db
            'questions_created': 0
        }

        # --- Add to Database ---
        try:
            add_teacher_to_db(teacher_uid, teacher_data)
            flash(f'Teacher "{name}" added successfully!', 'success')
            return redirect(url_for('admin.manage_teachers')) # Redirect to manage page

        except Exception as e:
            flash(f'Error adding teacher: {e}', 'danger')
            # Attempt cleanup - Best effort
            try:
                # This only deletes from RTDB, not Firebase Auth if you used that separately
                delete_firebase_auth_user(teacher_uid)
            except Exception as cleanup_e:
                 flash(f'Additionally, cleanup failed: {cleanup_e}', 'warning')
            return redirect(url_for('admin.add_teacher')) # Stay on add page on error

    # --- GET Request Handling ---
    else:
        try:
            subjects = get_all_subjects()
            if not subjects:
                flash('No subjects found. Please add subjects first.', 'warning')
        except Exception as e:
            flash(f'Error loading data for form: {e}', 'danger')
            subjects = {}

        return render_template('admin/add_teacher.html', subjects=subjects)

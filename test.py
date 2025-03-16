def create_admin(email, name, password, other_data=None):
    """Create a new admin with encrypted password"""
    firebase_email_key = email.replace('.', ',')

    # Create user data with hashed password
    user_data = {
        "email": email,
        "name": name,
        "password": hash_password(password)
    }

    # Add any additional data
    if other_data:
        user_data.update(other_data)

    # Save to Firebase
    admin_ref = database.child(f'administrators/admins/{firebase_email_key}')
    admin_ref.set(user_data)
    return True


def create_teacher(email, name, password, other_data=None):
    """Create a new teacher with encrypted password"""
    firebase_email_key = email.replace('.', ',')

    # Create user data with hashed password
    user_data = {
        "email": email,
        "name": name,
        "password": hash_password(password)
    }

    # Add any additional data
    if other_data:
        user_data.update(other_data)

    # Save to Firebase
    teacher_ref = database.child(f'administrators/teachers/{firebase_email_key}')
    teacher_ref.set(user_data)
    return True


def create_student(email, name, password, other_data=None):
    """Create a new student with encrypted password"""
    firebase_email_key = email.replace('.', ',')

    # Create user data with hashed password
    user_data = {
        "email": email,
        "name": name,
        "password": hash_password(password)
    }

    # Add any additional data
    if other_data:
        user_data.update(other_data)

    # Save to Firebase
    student_ref = database.child(f'students/{firebase_email_key}')
    student_ref.set(user_data)
    return True
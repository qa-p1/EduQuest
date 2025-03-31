from app.utils.database import database
from app.utils.auth import check_password


def authenticate_user(email, password, user_type):
    try:
        firebase_email_key = email.replace('.', ',')

        if user_type == 'admin':
            admin_ref = database.child(f'administrators/admins/{firebase_email_key}')
            admin_data = admin_ref.get()
            if admin_data and check_password(admin_data.get("password"), password):
                return {
                    'user_id': firebase_email_key,
                    'email': email,
                    'user_type': 'admin',
                    'name': admin_data.get("name", "Admin")
                }

        elif user_type == 'teacher':
            teacher_ref = database.child(f'administrators/teachers/{firebase_email_key}')
            teacher_data = teacher_ref.get()
            if teacher_data and check_password(teacher_data.get("password"), password):
                return {
                    'user_id': firebase_email_key,
                    'email': email,
                    'user_type': 'teacher',
                    'name': teacher_data.get("name", "Teacher")
                }

        elif user_type == 'student':
            student_ref = database.child(f'students/{firebase_email_key}')
            student_data = student_ref.get()
            if student_data and check_password(student_data.get("password"), password):
                return {
                    'user_id': firebase_email_key,
                    'email': email,
                    'user_type': 'student',
                    'name': student_data.get("name", "Student"),
                    'active': student_data.get("active", False)
                }

        return None

    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return None
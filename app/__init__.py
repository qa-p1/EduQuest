from flask import Flask
from firebase_admin import credentials, db
import firebase_admin
import os
import json
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')

    try:
        firebase_admin.get_app()
    except ValueError:
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')

        if service_account_json:
            try:
                service_account_info = json.loads(service_account_json)
                firebase_credentials = credentials.Certificate(service_account_info)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from environment variable: {e}")
                raise

        firebase_admin.initialize_app(firebase_credentials, {
            'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
        })

    # Import and register blueprints
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.teacher import teacher_bp
    from app.routes.admin import admin_bp
    from app.routes.question import question_bp
    from app.routes.common import common_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(question_bp)
    app.register_blueprint(common_bp)

    from app.utils.menu import inject_menu_items
    app.context_processor(inject_menu_items)

    return app
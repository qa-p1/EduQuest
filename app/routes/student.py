from flask import Blueprint, render_template, session
from app.utils.auth import login_required

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/')
@login_required(user_types=['student'])
def dashboard():
    return render_template('student/dashboard.html')


@student_bp.route('/quiz')
@login_required(user_types=['student'])
def quiz():
    return render_template('student/quiz.html', subjects=session['subjects'])

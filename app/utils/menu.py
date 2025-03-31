import os
from flask import current_app, session


def get_menu_items(user_type):
    menu_items = []

    base_dir = os.path.join(current_app.root_path, 'templates')

    user_type_dir = os.path.join(base_dir, user_type)
    if os.path.isdir(user_type_dir):

        files = [f for f in os.listdir(user_type_dir) if f.endswith('.html')]
        for file in files:

            name = os.path.splitext(file)[0]

            if name in ['base', 'layout', 'components']:
                continue

            display_name = name.replace('_', ' ').title()

            route_name = name

            icon_mapping = {
                'dashboard': 'fas fa-home',
                'profile': 'fas fa-user',
                'students': 'fas fa-users',
                'manage_students': 'fas fa-users',
                'exams': 'fas fa-file-alt',
                'generate_exam': 'fas fa-file-alt',
                'submissions': 'fas fa-clipboard-check',
                'quiz': 'fas fa-question-circle',
                'results': 'fas fa-chart-bar',
                'settings': 'fas fa-cog',
                'subjects': 'fas fa-book',
                'add_subject': 'fas fa-book',
                'add_question': 'fas fa-plus-circle',
                'teachers': 'fas fa-chalkboard-teacher'
            }

            icon = icon_mapping.get(name, 'fas fa-circle')

            menu_items.append({
                'name': display_name,
                'route': route_name,
                'icon': icon
            })

    return menu_items


def inject_menu_items():
    if 'menu_items' in session:
        return {'menu_items': session.get('menu_items', [])}
    elif 'user_type' in session:
        menu_items = get_menu_items(session.get('user_type'))
        session['menu_items'] = menu_items
        return {'menu_items': menu_items}
    return {'menu_items': []}

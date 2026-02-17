from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import database as db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Инициализация базы данных
db.init_db()

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'info'


class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.email = user_dict['email']
        self.is_admin = bool(user_dict['is_admin'])


@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        latest_ideas = db.get_latest_ideas(limit=3)
        popular_ideas = db.get_popular_ideas(limit=3)
        implemented_ideas = db.get_all_ideas(status='implemented', limit=3)
        cities = db.get_all_cities()
    else:
        latest_ideas = []
        popular_ideas = []
        implemented_ideas = []
        cities = db.get_all_cities()[:3]

    return render_template('index.html',
                           latest_ideas=latest_ideas,
                           popular_ideas=popular_ideas,
                           implemented_ideas=implemented_ideas,
                           cities=cities)


@app.route('/map')
@login_required
def map_page():
    city_id = request.args.get('city_id', type=int)
    add_idea = request.args.get('add_idea', 'false') == 'true'
    show_implemented = request.args.get('show_implemented', 'false') == 'true'

    city = None
    if city_id:
        city = db.get_city_by_id(city_id)

    if not city:
        cities_list = db.get_all_cities()
        if cities_list:
            city = cities_list[0]

    ideas = []
    if city_id:
        if show_implemented:
            ideas = db.get_all_ideas(status='implemented', city_id=city_id)
        else:
            ideas = db.get_all_ideas(status='approved', city_id=city_id)
    else:
        if show_implemented:
            ideas = db.get_all_ideas(status='implemented')
        else:
            ideas = db.get_all_ideas(status='approved')

    cities = db.get_all_cities()

    return render_template('map.html',
                           ideas=ideas,
                           city=city,
                           cities=cities,
                           add_idea=add_idea,
                           show_implemented=show_implemented)


@app.route('/ideas')
@login_required
def ideas_list():
    category = request.args.get('category', 'all')
    city_id = request.args.get('city_id', type=int)
    status = request.args.get('status', 'approved')

    # Ограничиваем доступные статусы для обычных пользователей
    if status not in ['approved', 'implemented']:
        status = 'approved'

    ideas = db.get_all_ideas(
        status=status,
        category=category if category != 'all' else None,
        city_id=city_id if city_id else None
    )

    categories = ['спорт', 'культура', 'детский досуг', 'экология', 'транспорт', 'благоустройство']
    cities = db.get_all_cities()

    return render_template('ideas.html',
                           ideas=ideas,
                           categories=categories,
                           selected_category=category,
                           cities=cities,
                           selected_city_id=city_id,
                           selected_status=status)


# Новый маршрут для реализованных идей
@app.route('/implemented')
@login_required
def implemented_ideas():
    category = request.args.get('category', 'all')
    city_id = request.args.get('city_id', type=int)

    ideas = db.get_all_ideas(
        status='implemented',
        category=category if category != 'all' else None,
        city_id=city_id if city_id else None
    )

    categories = ['спорт', 'культура', 'детский досуг', 'экология', 'транспорт', 'благоустройство']
    cities = db.get_all_cities()

    return render_template('implemented.html',
                           ideas=ideas,
                           categories=categories,
                           selected_category=category,
                           cities=cities,
                           selected_city_id=city_id)


@app.route('/add_idea', methods=['GET', 'POST'])
@login_required
def add_idea():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '')
        latitude = request.form.get('latitude', '').strip()
        longitude = request.form.get('longitude', '').strip()
        city_id = request.form.get('city_id', type=int) or None

        errors = []
        if not title:
            errors.append('Название обязательно')
        if not description:
            errors.append('Описание обязательно')
        if not category:
            errors.append('Категория обязательна')

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            errors.append('Координаты должны быть числами')

        if errors:
            for error in errors:
                flash(error, 'danger')
            categories = ['спорт', 'культура', 'детский досуг', 'экология', 'транспорт', 'благоустройство',
                          'образование', 'здравоохранение']
            cities = db.get_all_cities()
            return render_template('add_idea.html',
                                   categories=categories,
                                   cities=cities,
                                   default_latitude=latitude,
                                   default_longitude=longitude,
                                   default_city_id=city_id)

        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{timestamp}_{filename}"

                    upload_folder = app.config['UPLOAD_FOLDER']
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)

                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    image_path = filename

        idea_id = db.create_idea(title, description, category, latitude, longitude,
                                 current_user.id, city_id, image_path)

        flash('Идея успешно добавлена и отправлена на модерацию!', 'success')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    latitude = request.args.get('lat', '')
    longitude = request.args.get('lng', '')
    city_id = request.args.get('city_id', type=int)

    categories = ['спорт', 'культура', 'детский досуг', 'экология', 'транспорт', 'благоустройство', 'образование',
                  'здравоохранение']
    cities = db.get_all_cities()

    return render_template('add_idea.html',
                           categories=categories,
                           cities=cities,
                           default_latitude=latitude,
                           default_longitude=longitude,
                           default_city_id=city_id)


@app.route('/idea/<int:idea_id>')
@login_required
def idea_detail(idea_id):
    idea = db.get_idea_by_id(idea_id, increment_views=True)
    if not idea:
        abort(404)

    if idea['status'] != 'approved' and idea['status'] != 'implemented' and \
            (not current_user.is_authenticated or
             (not current_user.is_admin and current_user.id != idea['user_id'])):
        abort(403)

    return render_template('idea_detail.html', idea=idea)


@app.route('/vote/<int:idea_id>')
@login_required
def vote_idea(idea_id):
    idea = db.get_idea_by_id(idea_id, increment_views=False)

    # Проверяем, что идея одобрена (нельзя голосовать за реализованные или на модерации)
    if idea and idea['status'] == 'approved':
        if db.add_vote(current_user.id, idea_id):
            flash('Ваш голос учтен!', 'success')
        else:
            flash('Вы уже голосовали за эту идею!', 'warning')
    else:
        flash('За эту идею нельзя голосовать!', 'warning')

    return redirect(request.referrer or url_for('ideas_list'))


@app.route('/add_comment/<int:idea_id>', methods=['POST'])
@login_required
def add_comment(idea_id):
    idea = db.get_idea_by_id(idea_id, increment_views=False)

    # Проверяем, что идея одобрена или реализована
    if idea and (idea['status'] == 'approved' or idea['status'] == 'implemented'):
        text = request.form.get('text', '').strip()
        if not text:
            flash('Комментарий не может быть пустым', 'warning')
            return redirect(request.referrer or url_for('idea_detail', idea_id=idea_id))

        db.add_comment(text, current_user.id, idea_id)
        flash('Комментарий добавлен!', 'success')
        return redirect(url_for('idea_detail', idea_id=idea_id))
    else:
        flash('Комментарии к этой идее закрыты!', 'warning')
        return redirect(url_for('ideas_list'))


# Административные маршруты
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    pending_ideas = db.get_all_ideas(status='pending')
    approved_ideas = db.get_all_ideas(status='approved')
    implemented_ideas = db.get_all_ideas(status='implemented')
    stats = db.get_stats()

    return render_template('admin.html',
                           pending_ideas=pending_ideas,
                           approved_ideas=approved_ideas,
                           implemented_ideas=implemented_ideas,
                           total_ideas=stats['total_ideas'],
                           total_users=stats['total_users'],
                           total_votes=stats['total_votes'],
                           total_cities=stats['total_cities'])


@app.route('/admin/approve_idea/<int:idea_id>')
@login_required
def approve_idea(idea_id):
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    db.update_idea_status(idea_id, 'approved')
    flash('Идея одобрена!', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/reject_idea/<int:idea_id>')
@login_required
def reject_idea(idea_id):
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    db.update_idea_status(idea_id, 'rejected')
    flash('Идея отклонена!', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/implement_idea/<int:idea_id>')
@login_required
def implement_idea(idea_id):
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    db.update_idea_status(idea_id, 'implemented')
    flash('Идея помечена как реализованная!', 'success')
    return redirect(url_for('admin_panel'))


# Удаление идеи (для админов и авторов)
@app.route('/delete_idea/<int:idea_id>')
@login_required
def delete_idea(idea_id):
    idea = db.get_idea_by_id(idea_id, increment_views=False)

    if not idea:
        flash('Идея не найдена!', 'danger')
        return redirect(url_for('index'))

    if not current_user.is_admin and current_user.id != idea['user_id']:
        flash('Вы не можете удалить эту идею!', 'danger')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    db.delete_idea(idea_id)
    flash('Идея успешно удалена!', 'success')

    if request.referrer and 'admin' in request.referrer:
        return redirect(url_for('admin_panel'))
    elif current_user.is_admin:
        return redirect(url_for('admin_panel'))
    else:
        return redirect(url_for('profile'))


# Управление городами
@app.route('/admin/cities')
@login_required
def admin_cities():
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    cities = db.get_all_cities(active_only=False)
    return render_template('admin_cities.html', cities=cities)


@app.route('/admin/cities/add', methods=['GET', 'POST'])
@login_required
def admin_add_city():
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        latitude = request.form.get('latitude', '').strip()
        longitude = request.form.get('longitude', '').strip()
        zoom = request.form.get('zoom', 12)
        is_active = 'is_active' in request.form

        errors = []
        if not name:
            errors.append('Название города обязательно')

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            zoom = int(zoom)
        except ValueError:
            errors.append('Координаты и масштаб должны быть числами')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('admin_add_city'))

        city_id = db.create_city(name, description, latitude, longitude, zoom, is_active)
        if city_id:
            flash(f'Город "{name}" успешно добавлен!', 'success')
            return redirect(url_for('admin_cities'))
        else:
            flash('Город с таким названием уже существует!', 'danger')
            return redirect(url_for('admin_add_city'))

    return render_template('admin_city_form.html', city=None)


@app.route('/admin/cities/edit/<int:city_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_city(city_id):
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    city = db.get_city_by_id(city_id)
    if not city:
        flash('Город не найден!', 'danger')
        return redirect(url_for('admin_cities'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        latitude = float(request.form.get('latitude', '').strip())
        longitude = float(request.form.get('longitude', '').strip())
        zoom = int(request.form.get('zoom', 12))
        is_active = 'is_active' in request.form

        db.update_city(city_id, name, description, latitude, longitude, zoom, is_active)

        flash(f'Город "{name}" успешно обновлен!', 'success')
        return redirect(url_for('admin_cities'))

    return render_template('admin_city_form.html', city=city)


@app.route('/admin/cities/delete/<int:city_id>')
@login_required
def admin_delete_city(city_id):
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('index'))

    db.delete_city(city_id)
    flash('Город успешно удален!', 'success')
    return redirect(url_for('admin_cities'))


# API для получения данных
@app.route('/api/ideas')
@login_required
def api_ideas():
    city_id = request.args.get('city_id', type=int)
    status = request.args.get('status', 'approved')

    # Ограничиваем доступные статусы
    if status not in ['approved', 'implemented']:
        status = 'approved'

    ideas = db.get_all_ideas(status=status, city_id=city_id)

    result = []
    for idea in ideas:
        item = {
            'id': idea['id'],
            'title': idea['title'],
            'description': idea['description'],
            'category': idea['category'],
            'lat': idea['latitude'],
            'lng': idea['longitude'],
            'votes': idea['votes_count'],
            'user': idea['username'],
            'created_at': idea['created_at'],
            'status': idea['status']
        }
        if idea.get('image_path'):
            item['image_url'] = f"/static/uploads/{idea['image_path']}"
        result.append(item)

    return jsonify(result)


@app.route('/api/cities')
def api_cities():
    cities = db.get_all_cities()
    result = []
    for city in cities:
        result.append({
            'id': city['id'],
            'name': city['name'],
            'latitude': city['latitude'],
            'longitude': city['longitude'],
            'zoom': city['zoom']
        })
    return jsonify(result)


# Статистика (только для админов)
@app.route('/stats')
@login_required
def stats():
    if not current_user.is_admin:
        flash('Доступ к статистике имеют только администраторы!', 'danger')
        return redirect(url_for('index'))

    stats_data = db.get_stats()
    return render_template('stats.html', **stats_data)


# Страница профиля пользователя
@app.route('/profile')
@login_required
def profile():
    user_ideas = db.get_ideas_by_user(current_user.id)
    user_stats = db.get_user_stats(current_user.id)

    return render_template('profile.html',
                           user=current_user,
                           ideas=user_ideas,
                           user_stats=user_stats)


# Аутентификация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []

        if len(username) < 3 or len(username) > 80:
            errors.append('Имя пользователя должно быть от 3 до 80 символов')

        if len(password) < 6:
            errors.append('Пароль должен содержать не менее 6 символов')

        if password != confirm_password:
            errors.append('Пароли не совпадают')

        if db.get_user_by_username(username):
            errors.append('Пользователь с таким именем уже существует')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        user_id = db.create_user(username, email, password)
        if user_id:
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Ошибка при создании пользователя!', 'danger')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user_data = db.get_user_by_username(username)

        if user_data:
            if check_password_hash(user_data['password_hash'], password):
                user = User(user_data)
                login_user(user)
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('index'))

        flash('Неверное имя пользователя или пароль!', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/api/add_idea_from_map', methods=['POST'])
@login_required
def api_add_idea_from_map():
    try:
        data = request.get_json()

        if not data.get('title') or not data.get('description') or not data.get('category'):
            return jsonify({
                'success': False,
                'message': 'Заполните все обязательные поля'
            }), 400

        idea_id = db.create_idea(
            title=data['title'],
            description=data['description'],
            category=data['category'],
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            user_id=current_user.id,
            city_id=data.get('city_id'),
            image_path=None
        )

        if idea_id:
            return jsonify({
                'success': True,
                'message': 'Идея успешно добавлена и отправлена на модерацию!',
                'idea_id': idea_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ошибка при создании идеи'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}'
        }), 500


@app.route('/map/add_idea_from_click', methods=['POST'])
@login_required
def map_add_idea_from_click():
    try:
        data = request.get_json()

        if not data.get('title') or not data.get('description') or not data.get('category'):
            return jsonify({
                'success': False,
                'message': 'Пожалуйста, заполните все обязательные поля'
            }), 400

        try:
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'Неверные координаты'
            }), 400

        idea_id = db.create_idea(
            title=data['title'],
            description=data['description'],
            category=data['category'],
            latitude=latitude,
            longitude=longitude,
            user_id=current_user.id,
            city_id=data.get('city_id'),
            image_path=None
        )

        return jsonify({
            'success': True,
            'message': 'Идея успешно добавлена и отправлена на модерацию!',
            'idea_id': idea_id
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}'
        }), 500


@app.route('/add_idea_ajax', methods=['POST'])
@login_required
def add_idea_ajax():
    try:
        data = request.get_json()

        idea_id = db.create_idea(
            data['title'],
            data['description'],
            data['category'],
            float(data['latitude']),
            float(data['longitude']),
            current_user.id,
            data.get('city_id'),
            None
        )

        return jsonify({
            'success': True,
            'message': 'Идея успешно добавлена и отправлена на модерацию!',
            'idea_id': idea_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        })


# Обработка ошибок
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True, host='0.0.0.0', port=5000)

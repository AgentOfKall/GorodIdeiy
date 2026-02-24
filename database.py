import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = 'database.db'

def get_db():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных - создание таблиц"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица городов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        zoom INTEGER DEFAULT 12,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица идей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        user_id INTEGER NOT NULL,
        city_id INTEGER,
        status TEXT DEFAULT 'pending',
        votes_count INTEGER DEFAULT 0,
        views_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        image_path TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (city_id) REFERENCES cities (id)
    )
    ''')
    
    # Таблица голосов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        idea_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (idea_id) REFERENCES ideas (id),
        UNIQUE(user_id, idea_id)
    )
    ''')
    
    # Таблица комментариев
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        idea_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (idea_id) REFERENCES ideas (id)
    )
    ''')
    
    # Создаем администратора по умолчанию
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        password_hash = generate_password_hash('admin123')
        cursor.execute('''
        INSERT INTO users (username, email, password_hash, is_admin)
        VALUES (?, ?, ?, 1)
        ''', ('admin', 'admin@city.ru', password_hash))
    
    # Создаем тестовые города
    cursor.execute('SELECT id FROM cities')
    if not cursor.fetchone():
        cities = [
            ('Кисилевск', 'Промышленный центр Кемеровской области', 54.0000, 86.5833, 12),
            ('Кемерово', 'Столица Кузбасса', 55.3544, 86.0878, 12),
            ('Новокузнецк', 'Крупнейший город Кузбасса', 53.7557, 87.1094, 12),
        ]
        for city in cities:
            cursor.execute('''
            INSERT INTO cities (name, description, latitude, longitude, zoom)
            VALUES (?, ?, ?, ?, ?)
            ''', city)
    
    conn.commit()
    conn.close()

# Функции для работы с пользователями
def create_user(username, email, password):
    """Создание нового пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute('''
        INSERT INTO users (username, email, password_hash)
        VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    """Получение пользователя по имени"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    """Получение пользователя по ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

# Функции для работы с городами
def get_all_cities(active_only=True):
    """Получение всех городов"""
    conn = get_db()
    cursor = conn.cursor()
    if active_only:
        cursor.execute('SELECT * FROM cities WHERE is_active = 1 ORDER BY name')
    else:
        cursor.execute('SELECT * FROM cities ORDER BY name')
    cities = cursor.fetchall()
    conn.close()
    return [dict(city) for city in cities]

def get_city_by_id(city_id):
    """Получение города по ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cities WHERE id = ?', (city_id,))
    city = cursor.fetchone()
    conn.close()
    return dict(city) if city else None

def create_city(name, description, latitude, longitude, zoom=12, is_active=True):
    """Создание нового города"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO cities (name, description, latitude, longitude, zoom, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, latitude, longitude, zoom, 1 if is_active else 0))
        city_id = cursor.lastrowid
        conn.commit()
        return city_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def update_city(city_id, name, description, latitude, longitude, zoom, is_active):
    """Обновление города"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE cities 
    SET name = ?, description = ?, latitude = ?, longitude = ?, zoom = ?, is_active = ?
    WHERE id = ?
    ''', (name, description, latitude, longitude, zoom, 1 if is_active else 0, city_id))
    conn.commit()
    conn.close()

def delete_city(city_id):
    """Удаление города"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cities WHERE id = ?', (city_id,))
    conn.commit()
    conn.close()

# Функции для работы с идеями
def create_idea(title, description, category, latitude, longitude, user_id, city_id=None, image_path=None):
    """Создание новой идеи"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO ideas (title, description, category, latitude, longitude, user_id, city_id, image_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, category, latitude, longitude, user_id, city_id, image_path))
    idea_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return idea_id

def get_all_ideas(status=None, category=None, city_id=None, user_id=None, limit=None, offset=0, order_by='created_at DESC'):
    """Получение всех идей с фильтрами"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = '''
    SELECT ideas.*, users.username, cities.name as city_name
    FROM ideas 
    LEFT JOIN users ON ideas.user_id = users.id
    LEFT JOIN cities ON ideas.city_id = cities.id
    '''
    
    conditions = []
    params = []
    
    if status:
        conditions.append('ideas.status = ?')
        params.append(status)
    
    if category and category != 'all':
        conditions.append('ideas.category = ?')
        params.append(category)
    
    if city_id:
        conditions.append('ideas.city_id = ?')
        params.append(city_id)
    
    if user_id:
        conditions.append('ideas.user_id = ?')
        params.append(user_id)
    
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    query += f' ORDER BY ideas.{order_by}'
    
    if limit:
        query += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])
    
    cursor.execute(query, params)
    ideas = cursor.fetchall()
    conn.close()
    
    result = []
    for idea in ideas:
        idea_dict = dict(idea)
        # Получаем комментарии
        idea_dict['comments'] = get_comments_by_idea(idea_dict['id'])
        result.append(idea_dict)
    
    return result

def get_idea_by_id(idea_id, increment_views=True):
    """Получение идеи по ID"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT ideas.*, users.username, cities.name as city_name
    FROM ideas 
    LEFT JOIN users ON ideas.user_id = users.id
    LEFT JOIN cities ON ideas.city_id = cities.id
    WHERE ideas.id = ?
    ''', (idea_id,))
    
    idea = cursor.fetchone()
    
    if idea and increment_views:
        cursor.execute('UPDATE ideas SET views_count = views_count + 1 WHERE id = ?', (idea_id,))
        conn.commit()
    
    conn.close()
    
    if idea:
        idea_dict = dict(idea)
        idea_dict['comments'] = get_comments_by_idea(idea_id)
        return idea_dict
    return None

def get_ideas_by_user(user_id):
    """Получение идей пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT ideas.*, users.username, cities.name as city_name
    FROM ideas 
    LEFT JOIN users ON ideas.user_id = users.id
    LEFT JOIN cities ON ideas.city_id = cities.id
    WHERE ideas.user_id = ?
    ORDER BY ideas.created_at DESC
    ''', (user_id,))
    
    ideas = cursor.fetchall()
    conn.close()
    
    result = []
    for idea in ideas:
        idea_dict = dict(idea)
        # Получаем комментарии
        idea_dict['comments'] = get_comments_by_idea(idea_dict['id'])
        result.append(idea_dict)
    
    return result

def update_idea_status(idea_id, status):
    """Обновление статуса идеи"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE ideas SET status = ? WHERE id = ?', (status, idea_id))
    conn.commit()
    conn.close()

def delete_idea(idea_id):
    """Удаление идеи и связанных данных"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Получаем информацию об идее перед удалением (для удаления файла изображения)
    cursor.execute('SELECT image_path FROM ideas WHERE id = ?', (idea_id,))
    idea = cursor.fetchone()
    
    if idea and idea['image_path']:
        # Удаляем файл изображения
        image_path = os.path.join('static/uploads', idea['image_path'])
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass  # Игнорируем ошибки удаления файла
    
    # Удаляем связанные комментарии
    cursor.execute('DELETE FROM comments WHERE idea_id = ?', (idea_id,))
    
    # Удаляем связанные голоса
    cursor.execute('DELETE FROM votes WHERE idea_id = ?', (idea_id,))
    
    # Удаляем саму идею
    cursor.execute('DELETE FROM ideas WHERE id = ?', (idea_id,))
    
    conn.commit()
    conn.close()
    return True

def get_popular_ideas(limit=5):
    """Получение популярных идей"""
    return get_all_ideas(status='approved', limit=limit, order_by='votes_count DESC')

def get_latest_ideas(limit=5):
    """Получение последних идей"""
    return get_all_ideas(status='approved', limit=limit)

# Функции для работы с голосами
def add_vote(user_id, idea_id):
    """Добавление голоса за идею"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем, голосовал ли уже пользователь
    cursor.execute('SELECT id FROM votes WHERE user_id = ? AND idea_id = ?', (user_id, idea_id))
    if cursor.fetchone():
        conn.close()
        return False
    
    # Добавляем голос
    cursor.execute('INSERT INTO votes (user_id, idea_id) VALUES (?, ?)', (user_id, idea_id))
    # Увеличиваем счетчик голосов у идеи
    cursor.execute('UPDATE ideas SET votes_count = votes_count + 1 WHERE id = ?', (idea_id,))
    
    conn.commit()
    conn.close()
    return True

def get_votes_by_idea(idea_id):
    """Получение голосов для идеи"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM votes WHERE idea_id = ?', (idea_id,))
    votes = cursor.fetchall()
    conn.close()
    return [dict(vote) for vote in votes]

def get_user_votes(user_id):
    """Получение голосов пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT idea_id FROM votes WHERE user_id = ?', (user_id,))
    votes = cursor.fetchall()
    conn.close()
    return [vote['idea_id'] for vote in votes]

# Функции для работы с комментариями
def add_comment(text, user_id, idea_id):
    """Добавление комментария"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO comments (text, user_id, idea_id) VALUES (?, ?, ?)', (text, user_id, idea_id))
    comment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return comment_id

def get_comments_by_idea(idea_id):
    """Получение комментариев для идеи"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT comments.*, users.username 
    FROM comments 
    LEFT JOIN users ON comments.user_id = users.id 
    WHERE idea_id = ? 
    ORDER BY comments.created_at
    ''', (idea_id,))
    comments = cursor.fetchall()
    conn.close()
    return [dict(comment) for comment in comments]

# Статистика
def get_stats():
    """Получение статистики"""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Общая статистика
    cursor.execute('SELECT COUNT(*) FROM ideas')
    stats['total_ideas'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM ideas WHERE status = ?', ('approved',))
    stats['approved_ideas'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM ideas WHERE status = ?', ('pending',))
    stats['pending_ideas'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM ideas WHERE status = ?', ('implemented',))
    stats['implemented_ideas'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users')
    stats['total_users'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM votes')
    stats['total_votes'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comments')
    stats['total_comments'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM cities WHERE is_active = 1')
    stats['total_cities'] = cursor.fetchone()[0]
    
    # Статистика по категориям
    cursor.execute('SELECT category, COUNT(*) as count FROM ideas WHERE status = "approved" GROUP BY category')
    stats['categories'] = []
    for row in cursor.fetchall():
        stats['categories'].append({'category': row[0], 'count': row[1]})
    
    # Статистика по городам
    cursor.execute('''
    SELECT cities.name, COUNT(ideas.id) as count 
    FROM cities 
    LEFT JOIN ideas ON cities.id = ideas.city_id 
    GROUP BY cities.id
    ''')
    stats['cities_stats'] = []
    for row in cursor.fetchall():
        stats['cities_stats'].append({'name': row[0], 'count': row[1]})
    
    # Идеи за последние 7 дней
    cursor.execute('SELECT COUNT(*) FROM ideas WHERE created_at >= datetime("now", "-7 days")')
    stats['recent_ideas'] = cursor.fetchone()[0]
    
    # Самые активные пользователи
    cursor.execute('''
    SELECT users.username, COUNT(ideas.id) as ideas_count 
    FROM users 
    LEFT JOIN ideas ON users.id = ideas.user_id 
    GROUP BY users.id 
    ORDER BY ideas_count DESC 
    LIMIT 10
    ''')
    stats['active_users'] = []
    for row in cursor.fetchall():
        stats['active_users'].append({'username': row[0], 'ideas_count': row[1]})
    
    # Топ идей
    cursor.execute('''
    SELECT ideas.*, users.username 
    FROM ideas 
    LEFT JOIN users ON ideas.user_id = users.id
    WHERE ideas.status = "approved" 
    ORDER BY ideas.votes_count DESC 
    LIMIT 10
    ''')
    stats['top_ideas'] = []
    for row in cursor.fetchall():
        idea = dict(row)
        # Добавляем название города
        if idea.get('city_id'):
            city = get_city_by_id(idea['city_id'])
            if city:
                idea['city_name'] = city['name']
        stats['top_ideas'].append(idea)
    
    conn.close()
    return stats

def get_user_stats(user_id):
    """Получение статистики пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute('SELECT COUNT(*) FROM ideas WHERE user_id = ?', (user_id,))
    stats['ideas_count'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM votes WHERE user_id = ?', (user_id,))
    stats['votes_count'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comments WHERE user_id = ?', (user_id,))
    stats['comments_count'] = cursor.fetchone()[0]
    
    # Статистика по статусам идей
    cursor.execute('SELECT status, COUNT(*) as count FROM ideas WHERE user_id = ? GROUP BY status', (user_id,))
    stats['ideas_by_status'] = {}
    for row in cursor.fetchall():
        stats['ideas_by_status'][row[0]] = row[1]
    
    conn.close()
    return stats
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from models import db, User, City, Idea, Vote, Comment

# ------------------------------------------------------------
# Вспомогательные функции для преобразования объектов в словари
# ------------------------------------------------------------
def user_to_dict(user):
    if not user:
        return None
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin,
        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None
    }

def city_to_dict(city):
    if not city:
        return None
    return {
        'id': city.id,
        'name': city.name,
        'description': city.description,
        'latitude': city.latitude,
        'longitude': city.longitude,
        'zoom': city.zoom,
        'is_active': city.is_active,
        'created_at': city.created_at.strftime('%Y-%m-%d %H:%M:%S') if city.created_at else None
    }

def comment_to_dict(comment):
    if not comment:
        return None
    return {
        'id': comment.id,
        'text': comment.text,
        'user_id': comment.user_id,
        'username': comment.user.username if comment.user else None,
        'idea_id': comment.idea_id,
        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S') if comment.created_at else None
    }

def idea_to_dict(idea, include_comments=True):
    if not idea:
        return None
    d = {
        'id': idea.id,
        'title': idea.title,
        'description': idea.description,
        'category': idea.category,
        'latitude': idea.latitude,
        'longitude': idea.longitude,
        'user_id': idea.user_id,
        'username': idea.user.username if idea.user else None,
        'city_id': idea.city_id,
        'city_name': idea.city.name if idea.city else None,
        'status': idea.status,
        'votes_count': idea.votes_count,
        'views_count': idea.views_count,
        'created_at': idea.created_at.strftime('%Y-%m-%d %H:%M:%S') if idea.created_at else None,
        'image_path': idea.image_path,
    }
    if include_comments:
        d['comments'] = [comment_to_dict(c) for c in idea.comments]
    return d

# ------------------------------------------------------------
# Инициализация базы данных (создание таблиц и начальных данных)
# ------------------------------------------------------------
def init_db():
    """Создание таблиц и наполнение начальными данными"""
    db.create_all()

    # Создаём администратора, если нет
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@city.ru', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)

    # Создаём тестовые города, если нет
    if City.query.count() == 0:
        cities = [
            City(name='Киселевск', description='Промышленный центр Кемеровской области',
                 latitude=54.0000, longitude=86.5833, zoom=12),
            City(name='Кемерово', description='Столица Кузбасса',
                 latitude=55.3544, longitude=86.0878, zoom=12),
            City(name='Новокузнецк', description='Крупнейший город Кузбасса',
                 latitude=53.7557, longitude=87.1094, zoom=12),
        ]
        db.session.add_all(cities)

    db.session.commit()

# ------------------------------------------------------------
# Пользователи
# ------------------------------------------------------------
def create_user(username, email, password):
    try:
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id
    except Exception:
        db.session.rollback()
        return None

def get_user_by_username(username):
    user = User.query.filter_by(username=username).first()
    return user_to_dict(user)

def get_user_by_id(user_id):
    user = User.query.get(user_id)
    return user_to_dict(user)

# ------------------------------------------------------------
# Города
# ------------------------------------------------------------
def get_all_cities(active_only=True):
    query = City.query
    if active_only:
        query = query.filter_by(is_active=True)
    cities = query.order_by(City.name).all()
    return [city_to_dict(c) for c in cities]

def get_city_by_id(city_id):
    city = City.query.get(city_id)
    return city_to_dict(city)

def create_city(name, description, latitude, longitude, zoom=12, is_active=True):
    try:
        city = City(name=name, description=description, latitude=latitude,
                    longitude=longitude, zoom=zoom, is_active=is_active)
        db.session.add(city)
        db.session.commit()
        return city.id
    except Exception:
        db.session.rollback()
        return None

def update_city(city_id, name, description, latitude, longitude, zoom, is_active):
    city = City.query.get(city_id)
    if not city:
        return
    city.name = name
    city.description = description
    city.latitude = latitude
    city.longitude = longitude
    city.zoom = zoom
    city.is_active = is_active
    db.session.commit()

def delete_city(city_id):
    city = City.query.get(city_id)
    if city:
        db.session.delete(city)
        db.session.commit()

# ------------------------------------------------------------
# Идеи
# ------------------------------------------------------------
def create_idea(title, description, category, latitude, longitude, user_id, city_id=None, image_path=None):
    idea = Idea(
        title=title, description=description, category=category,
        latitude=latitude, longitude=longitude,
        user_id=user_id, city_id=city_id, image_path=image_path
    )
    db.session.add(idea)
    db.session.commit()
    return idea.id

def get_all_ideas(status=None, category=None, city_id=None, user_id=None,
                  limit=None, offset=0, order_by='created_at DESC'):
    query = Idea.query
    if status:
        query = query.filter_by(status=status)
    if category and category != 'all':
        query = query.filter_by(category=category)
    if city_id:
        query = query.filter_by(city_id=city_id)
    if user_id:
        query = query.filter_by(user_id=user_id)

    # Разбор order_by (ожидается строка вида "поле направление")
    # По умолчанию сортируем по created_at DESC
    if order_by:
        parts = order_by.split()
        field = parts[0]
        direction = parts[1] if len(parts) > 1 else 'DESC'
        if direction.upper() == 'DESC':
            query = query.order_by(getattr(Idea, field).desc())
        else:
            query = query.order_by(getattr(Idea, field).asc())

    if limit:
        query = query.limit(limit).offset(offset)

    ideas = query.all()
    return [idea_to_dict(i, include_comments=True) for i in ideas]

def get_idea_by_id(idea_id, increment_views=True):
    idea = Idea.query.get(idea_id)
    if not idea:
        return None
    if increment_views:
        idea.views_count += 1
        db.session.commit()
    return idea_to_dict(idea, include_comments=True)

def get_ideas_by_user(user_id):
    ideas = Idea.query.filter_by(user_id=user_id).order_by(Idea.created_at.desc()).all()
    return [idea_to_dict(i, include_comments=True) for i in ideas]

def update_idea_status(idea_id, status):
    idea = Idea.query.get(idea_id)
    if idea:
        idea.status = status
        db.session.commit()

def delete_idea(idea_id):
    idea = Idea.query.get(idea_id)
    if not idea:
        return True
    # Удаляем связанные файлы
    if idea.image_path:
        image_path = os.path.join('static/uploads', idea.image_path)
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass
    # Удаляем комментарии и голоса
    Comment.query.filter_by(idea_id=idea_id).delete()
    Vote.query.filter_by(idea_id=idea_id).delete()
    db.session.delete(idea)
    db.session.commit()
    return True

def get_popular_ideas(limit=5):
    return get_all_ideas(status='approved', limit=limit, order_by='votes_count DESC')

def get_latest_ideas(limit=5):
    return get_all_ideas(status='approved', limit=limit)

# ------------------------------------------------------------
# Голоса
# ------------------------------------------------------------
def add_vote(user_id, idea_id):
    # Проверяем, не голосовал ли уже
    existing = Vote.query.filter_by(user_id=user_id, idea_id=idea_id).first()
    if existing:
        return False
    vote = Vote(user_id=user_id, idea_id=idea_id)
    db.session.add(vote)
    # Увеличиваем счётчик голосов у идеи
    idea = Idea.query.get(idea_id)
    if idea:
        idea.votes_count += 1
    db.session.commit()
    return True

def get_votes_by_idea(idea_id):
    votes = Vote.query.filter_by(idea_id=idea_id).all()
    return [{'id': v.id, 'user_id': v.user_id, 'idea_id': v.idea_id,
             'created_at': v.created_at.strftime('%Y-%m-%d %H:%M:%S') if v.created_at else None}
            for v in votes]

def get_user_votes(user_id):
    votes = Vote.query.filter_by(user_id=user_id).all()
    return [v.idea_id for v in votes]

# ------------------------------------------------------------
# Комментарии
# ------------------------------------------------------------
def add_comment(text, user_id, idea_id):
    comment = Comment(text=text, user_id=user_id, idea_id=idea_id)
    db.session.add(comment)
    db.session.commit()
    return comment.id

def get_comments_by_idea(idea_id):
    comments = Comment.query.filter_by(idea_id=idea_id).order_by(Comment.created_at).all()
    return [comment_to_dict(c) for c in comments]

# ------------------------------------------------------------
# Статистика
# ------------------------------------------------------------
def get_stats():
    stats = {}

    stats['total_ideas'] = Idea.query.count()
    stats['approved_ideas'] = Idea.query.filter_by(status='approved').count()
    stats['pending_ideas'] = Idea.query.filter_by(status='pending').count()
    stats['implemented_ideas'] = Idea.query.filter_by(status='implemented').count()
    stats['total_users'] = User.query.count()
    stats['total_votes'] = Vote.query.count()
    stats['total_comments'] = Comment.query.count()
    stats['total_cities'] = City.query.filter_by(is_active=True).count()

    # Категории
    categories = db.session.query(Idea.category, func.count(Idea.id).label('count')) \
                           .filter(Idea.status == 'approved') \
                           .group_by(Idea.category).all()
    stats['categories'] = [{'category': cat, 'count': cnt} for cat, cnt in categories]

    # Города
    cities_stats = db.session.query(City.name, func.count(Idea.id).label('count')) \
                              .outerjoin(Idea, City.id == Idea.city_id) \
                              .group_by(City.id).all()
    stats['cities_stats'] = [{'name': name, 'count': cnt} for name, cnt in cities_stats]

    # Идеи за последние 7 дней
    week_ago = datetime.utcnow() - timedelta(days=7)
    stats['recent_ideas'] = Idea.query.filter(Idea.created_at >= week_ago).count()

    # Самые активные пользователи
    active = db.session.query(User.username, func.count(Idea.id).label('ideas_count')) \
                        .outerjoin(Idea, User.id == Idea.user_id) \
                        .group_by(User.id) \
                        .order_by(func.count(Idea.id).desc()) \
                        .limit(10).all()
    stats['active_users'] = [{'username': u, 'ideas_count': cnt} for u, cnt in active]

    # Топ идей
    top = Idea.query.filter_by(status='approved') \
                    .order_by(Idea.votes_count.desc()) \
                    .limit(10).all()
    stats['top_ideas'] = [idea_to_dict(idea, include_comments=False) for idea in top]

    return stats

def get_user_stats(user_id):
    stats = {}
    stats['ideas_count'] = Idea.query.filter_by(user_id=user_id).count()
    stats['votes_count'] = Vote.query.filter_by(user_id=user_id).count()
    stats['comments_count'] = Comment.query.filter_by(user_id=user_id).count()

    # Статусы идей
    status_counts = db.session.query(Idea.status, func.count(Idea.id)) \
                               .filter_by(user_id=user_id) \
                               .group_by(Idea.status).all()
    stats['ideas_by_status'] = {s: cnt for s, cnt in status_counts}
    return stats

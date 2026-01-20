#!/usr/bin/env python3
"""
Скрипт для настройки и запуска приложения "Город Идей"
"""

import os
import sys
import subprocess
import argparse

def create_directory_structure():
    """Создает структуру папок для приложения"""
    directories = [
        'templates',
        'static/css',
        'static/js',
        'static/uploads',
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Создана папка: {directory}")
    
    # Создаем файл .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# Database
*.db
*.sqlite3

# Uploads
static/uploads/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
    
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    print("✓ Создан файл .gitignore")

def install_requirements():
    """Устанавливает зависимости"""
    requirements = [
        'Flask==2.3.3',
        'Flask-SQLAlchemy==3.0.5',
        'Flask-Login==0.6.3',
        'Werkzeug==2.3.7',
    ]
    
    print("\nУстановка зависимостей...")
    for package in requirements:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    print("✓ Все зависимости установлены")

def create_admin_user():
    """Создает администратора по умолчанию"""
    from app import app, db, User
    
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@city.ru', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✓ Создан администратор: admin / admin123")
        else:
            print("✓ Администратор уже существует")

def main():
    parser = argparse.ArgumentParser(description='Настройка приложения "Город Идей"')
    parser.add_argument('--setup', action='store_true', help='Настроить приложение с нуля')
    parser.add_argument('--run', action='store_true', help='Запустить приложение')
    parser.add_argument('--reset-db', action='store_true', help='Сбросить базу данных')
    
    args = parser.parse_args()
    
    if args.setup:
        print("Начало настройки приложения...")
        create_directory_structure()
        install_requirements()
        
        # Импортируем и создаем базу данных
        from app import app, db
        with app.app_context():
            db.create_all()
            print("✓ База данных создана")
        
        create_admin_user()
        print("\n✅ Настройка завершена!")
        print("Запустите приложение командой: python app.py")
    
    elif args.reset_db:
        confirm = input("Вы уверены, что хотите сбросить базу данных? (y/n): ")
        if confirm.lower() == 'y':
            from app import app, db
            import os
            
            with app.app_context():
                # Удаляем все таблицы
                db.drop_all()
                print("✓ Все таблицы удалены")
                
                # Создаем заново
                db.create_all()
                print("✓ Новые таблицы созданы")
                
                # Создаем администратора
                create_admin_user()
            
            print("✅ База данных сброшена")
    
    elif args.run:
        print("Запуск приложения...")
        subprocess.run([sys.executable, "app.py"])
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
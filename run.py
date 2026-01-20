#!/usr/bin/env python3
"""
Простой скрипт для запуска приложения
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    # Создаем необходимые папки
    folders = ['static/uploads', 'static/css', 'static/js', 'templates']
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✓ Папка создана/проверена: {folder}")
    
    # Запускаем приложение
    print("🚀 Запуск приложения 'Город Идей'...")
    print("📊 Откройте в браузере: http://localhost:5000")
    print("👑 Админ: admin / admin123")
    app.run(debug=True, host='0.0.0.0', port=5000)
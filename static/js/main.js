// static/js/main.js

// Глобальные переменные для карты
let mapInstance = null;
let addIdeaMode = false;
let markersLayer = null;

// Инициализация карты
function initMap(lat, lng, zoom) {
    if (!mapInstance) {
        mapInstance = L.map('map').setView([lat, lng], zoom);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(mapInstance);
        
        // Добавляем слой для маркеров
        markersLayer = L.layerGroup().addTo(mapInstance);
        
        // Добавляем поиск
        L.Control.geocoder({
            defaultMarkGeocode: false
        }).on('markgeocode', function(e) {
            mapInstance.setView(e.geocode.center, 16);
        }).addTo(mapInstance);
        
        // Загружаем идеи
        loadIdeasOnMap();
    }
    return mapInstance;
}

// Загрузка идей на карту
function loadIdeasOnMap() {
    if (!mapInstance || !markersLayer) return;
    
    // Очищаем старые маркеры
    markersLayer.clearLayers();
    
    // Загружаем идеи с сервера
    fetch('/api/ideas')
        .then(response => response.json())
        .then(ideas => {
            ideas.forEach(idea => {
                const marker = L.marker([idea.lat, idea.lng])
                    .addTo(markersLayer)
                    .bindPopup(`
                        <div class="map-popup">
                            <h6>${idea.title}</h6>
                            <p><small>${idea.category} | 👍 ${idea.votes}</small></p>
                            <p>${idea.description.substring(0, 100)}...</p>
                            <a href="/idea/${idea.id}" class="btn btn-sm btn-primary">Подробнее</a>
                        </div>
                    `);
            });
        })
        .catch(error => console.error('Ошибка загрузки идей:', error));
}

// Включение/выключение режима добавления идей
function toggleAddIdeaMode() {
    addIdeaMode = !addIdeaMode;
    
    if (addIdeaMode && mapInstance) {
        // Включаем режим добавления
        mapInstance.on('click', onMapClickAddIdea);
        
        // Показываем инструкцию
        L.control.attribution({position: 'bottomright'})
            .addTo(mapInstance)
            .setPrefix('Кликните на карте для добавления идеи');
        
        document.getElementById('addIdeaBtn').textContent = 'Отменить добавление';
        document.getElementById('addIdeaBtn').classList.remove('btn-success');
        document.getElementById('addIdeaBtn').classList.add('btn-warning');
        
    } else if (mapInstance) {
        // Выключаем режим добавления
        mapInstance.off('click', onMapClickAddIdea);
        
        document.getElementById('addIdeaBtn').textContent = 'Добавить идею на карте';
        document.getElementById('addIdeaBtn').classList.remove('btn-warning');
        document.getElementById('addIdeaBtn').classList.add('btn-success');
    }
}

// Обработчик клика по карте для добавления идеи
function onMapClickAddIdea(e) {
    // Показываем модальное окно с координатами
    const modal = new bootstrap.Modal(document.getElementById('addIdeaModal'));
    
    // Заполняем координаты
    document.getElementById('modalLatitude').value = e.latlng.lat.toFixed(6);
    document.getElementById('modalLongitude').value = e.latlng.lng.toFixed(6);
    
    // Показываем модальное окно
    modal.show();
    
    // Добавляем временный маркер
    const tempMarker = L.marker(e.latlng, {
        icon: L.divIcon({
            className: 'temp-marker',
            html: '<div style="background-color: #dc3545; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>',
            iconSize: [24, 24]
        })
    }).addTo(mapInstance);
    
    // Удаляем маркер при закрытии модального окна
    document.getElementById('addIdeaModal').addEventListener('hidden.bs.modal', function () {
        if (mapInstance && tempMarker) {
            mapInstance.removeLayer(tempMarker);
        }
    }, { once: true });
}

// Отправка идеи с карты
function submitIdeaFromMap() {
    const formData = {
        title: document.getElementById('modalTitle').value,
        description: document.getElementById('modalDescription').value,
        category: document.getElementById('modalCategory').value,
        latitude: document.getElementById('modalLatitude').value,
        longitude: document.getElementById('modalLongitude').value,
        city_id: document.getElementById('modalCityId').value || null
    };
    
    // Валидация
    if (!formData.title || !formData.description || !formData.category) {
        alert('Пожалуйста, заполните все обязательные поля');
        return;
    }
    
    // Показываем индикатор загрузки
    const submitBtn = document.querySelector('#addIdeaModal .btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Отправка...';
    submitBtn.disabled = true;
    
    // Отправляем данные
    fetch('/api/add_idea_from_map', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Закрываем модальное окно
            bootstrap.Modal.getInstance(document.getElementById('addIdeaModal')).hide();
            
            // Показываем уведомление об успехе
            showNotification('Идея успешно добавлена! Она появится после модерации.', 'success');
            
            // Обновляем карту
            setTimeout(() => {
                loadIdeasOnMap();
            }, 1000);
            
        } else {
            alert('Ошибка: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка при отправке');
    })
    .finally(() => {
        // Восстанавливаем кнопку
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    });
}

// Вспомогательные функции
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, есть ли карта на странице
    if (document.getElementById('map')) {
        // Получаем координаты из данных страницы
        const mapData = document.getElementById('map').dataset;
        const lat = parseFloat(mapData.lat) || 55.7558;
        const lng = parseFloat(mapData.lng) || 37.6173;
        const zoom = parseInt(mapData.zoom) || 10;
        
        // Инициализируем карту
        initMap(lat, lng, zoom);
        
        // Инициализируем обработчики для кнопки добавления
        const addIdeaBtn = document.getElementById('addIdeaBtn');
        if (addIdeaBtn) {
            addIdeaBtn.addEventListener('click', toggleAddIdeaMode);
        }
    }
    
    // Инициализация форм
    const ideaForm = document.getElementById('addIdeaForm');
    if (ideaForm) {
        ideaForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitIdeaFromMap();
        });
    }
    
    // Получение геолокации для формы добавления идеи
    const getLocationBtn = document.getElementById('getLocationBtn');
    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const latInput = document.getElementById('latitude');
                        const lngInput = document.getElementById('longitude');
                        if (latInput && lngInput) {
                            latInput.value = position.coords.latitude.toFixed(6);
                            lngInput.value = position.coords.longitude.toFixed(6);
                        }
                    },
                    function(error) {
                        console.error('Ошибка геолокации:', error);
                    }
                );
            }
        });
    }
});
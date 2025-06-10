import json
import logging

import requests
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render

from .models import User, SearchHistory
from .utils import request_api, encrypt_user_id, decrypt_user_id, get_last_cities_from_cookie, update_last_cities


def home(request):
    """
    Главная страница приложения.
    Обрабатывает GET запрос с параметрами и POST запрос для работы с формой.
    """

    last_cities = get_last_cities_from_cookie(request)
    forecasts = None
    error_message = None

    encrypted_user_id = request.COOKIES.get('user_id')

    if encrypted_user_id:
        user_id = decrypt_user_id(str(encrypted_user_id))
        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                user = User.objects.create()
        else:
            user = User.objects.create()
    else:
        user = User.objects.create()

    if request.method == 'POST':
        city_name_from_user = request.POST.get('city_name')
    elif request.method == 'GET':
        city_name_from_user = request.GET.get('city_name')
    else:
        city_name_from_user = None

    if city_name_from_user:
        forecasts_answer = request_api(city_name_from_user)
        if forecasts_answer:
            error_message = forecasts_answer['error']
            forecasts = forecasts_answer['data']

            if error_message is None:
                SearchHistory.objects.create(user=user, city_name=city_name_from_user)
                last_cities = update_last_cities(last_cities, city_name_from_user)

        else:
            logging.error(f'Ошибка при запросе к API')

    context = {
        'message': 'Приветствуем! Введите название города, чтобы увидеть прогноз погоды.',
        'city_name': '',
        'last_cities': last_cities,
        'forecasts': forecasts,
        'error_message': error_message,
        'city_name_for_template': city_name_from_user or '',
    }

    response = render(request, 'home.html', context)

    # Обновление куков у пользователя
    if city_name_from_user:
        last_cities_json = json.dumps(last_cities)
        response.set_cookie('last_cities', last_cities_json, max_age=60 * 60 * 24 * 7)

    if user:
        expires_in_seconds = 60 * 60 * 24 * 30 * 6  # 6 месяцев
        encrypted_user_id = encrypt_user_id(str(user.user_id))
        response.set_cookie('user_id', encrypted_user_id, max_age=expires_in_seconds, httponly=True)

    return response


def city_search_count(_: requests.request):
    """ Точка доступа к API для получения количества запросов для каждого города """

    city_counts = SearchHistory.objects.values('city_name').annotate(count=Count('city_name')).order_by('-count')
    city_counts_list = list(city_counts)
    json_data = json.dumps(city_counts_list, ensure_ascii=False)
    return HttpResponse(json_data, content_type='application/json')

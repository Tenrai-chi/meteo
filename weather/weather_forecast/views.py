import json
import logging

from django.shortcuts import render

from .utils import request_api


def home(request):
    """
    Главная страница приложения.
    Обрабатывает GET запрос с параметрами и POST запрос для работы с формой.
    """

    last_cities = get_last_cities_from_cookie(request)
    forecasts = None
    error_message = None
    city_name_from_user = None

    if request.method == 'POST':
        city_name_from_user = request.POST.get('city_name')
        if city_name_from_user:
            forecasts_answer = request_api(city_name_from_user)
            if forecasts_answer:
                error_message = forecasts_answer['error']
                forecasts = forecasts_answer['data']
                last_cities = update_last_cities(last_cities, city_name_from_user)
            else:
                logging.error(f'Ошибка при запросе к API')
    elif request.method == 'GET':
        city_name_from_user = request.GET.get('city_name')
        if city_name_from_user:
            forecasts_answer = request_api(city_name_from_user)
            if forecasts_answer:
                error_message = forecasts_answer['error']
                forecasts = forecasts_answer['data']
                last_cities = update_last_cities(last_cities, city_name_from_user)

    context = {
        'message': 'Привет, пользователь! Введите название города, чтобы увидеть прогноз погоды.',
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

    return response


def get_last_cities_from_cookie(request) -> list:
    """ Извлекает список последних городов из куков """

    last_cities_json = request.COOKIES.get('last_cities')
    if last_cities_json:
        try:
            return json.loads(last_cities_json)
        except json.JSONDecodeError:
            logging.error(f'Ошибка при получении cookies')
            return []
    return []


def update_last_cities(last_cities: str, city_name: str) -> list:
    """ Обновление списка последних городов для отправки в куки пользователю """

    if city_name in last_cities:
        last_cities.remove(city_name)
    last_cities = [city_name] + last_cities
    return last_cities[:5]


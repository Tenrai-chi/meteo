import json

from django.shortcuts import render

from .utils import request_api


def home(request):
    """ Главная страница приложения.
        Логика изменена со стандартной отработки get-post запросов
    """

    # Получаем список последних городов из cookie
    last_cities_json = request.COOKIES.get('last_cities')
    last_cities = []
    if last_cities_json:
        try:
            last_cities = json.loads(last_cities_json)
        except json.JSONDecodeError:
            last_cities = []

    forecasts = None
    error_message = None

    # Ленивый отбор параметра для поиска, если передано через шаблон, берет город оттуда, если нет, то из параметров
    city_name_from_user = request.POST.get('city_name') or request.GET.get('city_name')

    if city_name_from_user:
        forecasts_upd = request_api(city_name_from_user)
        if forecasts_upd['error']:
            error_message = 'Не удалось получить погоду для этого города.'
            forecasts = None
        else:
            forecasts = forecasts_upd['data']
            # Обновление списка последних городов в куках
            if city_name_from_user in last_cities:
                last_cities.remove(city_name_from_user)
            last_cities.insert(0, city_name_from_user)
            last_cities = last_cities[:5]

    city_name_for_template = city_name_from_user or ''

    if city_name_from_user:
        response = render(request, 'home.html',
                          {'message': 'Привет, пользователь! Введите название города, чтобы увидеть прогноз погоды.',
                           'city_name': '', 'last_cities': last_cities, 'forecasts': forecasts,
                           'error_message': error_message,
                           'city_name_for_template': city_name_for_template})
        # Установка или обновление куки
        last_cities_json = json.dumps(last_cities)
        response.set_cookie('last_cities', last_cities_json, max_age=60 * 60 * 24 * 7)
        return response

    context = {
        'message': 'Привет, пользователь! Введите название города, чтобы увидеть прогноз погоды.',
        'city_name': '',
        'last_cities': last_cities,
        'forecasts': forecasts,
        'error_message': error_message,
        'city_name_for_template': city_name_for_template,
    }

    response = render(request, 'home.html', context)
    return response



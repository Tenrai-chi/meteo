""" Запросы к внешним ресурсам:
    - Координаты запрашиваемого города берутся из википедии парсером
    - Данные о погоде на 7 дней берутся с API open-meteo.com
"""

import openmeteo_requests
import pandas as pd
import requests
import requests_cache
import urllib

from bs4 import BeautifulSoup

from retry_requests import retry


def parse_coordinates(city_name: str) -> tuple | None:
    """ Берет координаты со страницы города в википедии.
        Возвращает кортеж координат при удачном получении.
        Возвращает None при ошибке
    """

    try:
        encoded_city_name = urllib.parse.quote(city_name)
        url = f'https://ru.wikipedia.org/wiki/{encoded_city_name}'
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        maplink = soup.find('a', class_='mw-kartographer-maplink')

        if maplink:
            latitude = maplink.get('data-lat')
            longitude = maplink.get('data-lon')

            if latitude and longitude:
                try:
                    lat = float(latitude)
                    lon = float(longitude)
                    return lat, lon
                except ValueError:
                    print('Ошибка в преобразовании координат')
            else:
                print('Не найдены значения широты и долготы')
        else:
            print('Не удалось координаты на странице')

    except requests.exceptions.RequestException as e:
        print(f'Ошибка при запросе: {e}')
    except Exception as e:
        print(f'Ошибка при парсинге: {e}')


def get_weather(latitude: float, longitude: float) -> list | None:
    """ Запрашивает прогноз погоды на 7 дней по координатам.
        Возвращает список из словарей, где каждый словарь - это прогноз на 1 день
        Возвращает None при ошибках
    """

    try:
        # Настройка повторных попыток запроса при ошибках
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': latitude,
            'longitude': longitude,
            # Запрос на температуру, влажность и скорость ветра на 7 дней
            'hourly': ['temperature_2m', 'relativehumidity_2m', 'windspeed_10m'],
            'forecast_days': 7  # Запрашиваем прогноз на 7 дней
        }
        response = openmeteo.weather_api(url, params=params)[0]

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_relativehumidity_2m = hourly.Variables(1).ValuesAsNumpy()
        hourly_windspeed_10m = hourly.Variables(2).ValuesAsNumpy()
        hourly_times = pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit='s', utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit='s', utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive='left'
        )
        hourly_data = {'date': hourly_times,
                       'temperature_2m': hourly_temperature_2m,
                       'relativehumidity_2m': hourly_relativehumidity_2m,
                       'windspeed_10m': hourly_windspeed_10m}

        hourly_dataframe = pd.DataFrame(data=hourly_data)

        daily_forecasts = []
        for i in range(7):
            day_data = hourly_dataframe[hourly_dataframe['date'].dt.day == hourly_dataframe['date'].dt.day.unique()[i]]
            hourly_forecasts = []
            for index, row in day_data.iterrows():
                hourly_forecast = {
                    'time': row['date'].strftime('%H:%M'),
                    'temperature': round(row['temperature_2m'], 1),
                    'humidity': round(row['relativehumidity_2m'], 1),
                    'windspeed': round(row['windspeed_10m'], 1),
                }
                hourly_forecasts.append(hourly_forecast)

            weekday = day_data['date'].iloc[0].strftime('%A')
            weather_data = {
                'date': day_data['date'].iloc[0].strftime('%Y-%m-%d'),
                'weekday': weekday,
                'hourly_data': hourly_forecasts,
            }
            daily_forecasts.append(weather_data)
        return daily_forecasts

    except Exception as e:
        print(f'Ошибка при получении погоды по координатам: {e}')


def request_api(city_name: str) -> dict:
    """ Объединение всей логики получения информации для вызова из view.
        Возвращает словарь, который содержит текст ошибки,
        если получены данные о погоде, то передает их по ключу 'data'
    """

    answer = parse_coordinates(city_name)
    if answer:
        latitude, longitude = answer
        data = get_weather(latitude, longitude)
        return {'data': data,
                'error': None}
    else:
        return {'error': 'Не удалось найти информацию о погоде в заданном городе'}



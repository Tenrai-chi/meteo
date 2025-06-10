import json
import uuid

from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch

from ..models import User, SearchHistory
from ..views import city_search_count
from ..utils import encrypt_user_id


class TestSearchHistoryAPI(TestCase):
    """ Тесты для точки доступа к API """

    def test_get_search_history_success(self):
        """ Получение непустой истории поисковых запросов """

        user = User.objects.create(user_id=uuid.uuid4())
        SearchHistory.objects.create(user=user, city_name='Москва')
        SearchHistory.objects.create(user=user, city_name='Москва')
        SearchHistory.objects.create(user=user, city_name='Токио')

        url = reverse(city_search_count)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)

        if data:
            self.assertIn('city_name', data[0])
            self.assertIn('count', data[0])
            self.assertIsInstance(data[0]['count'], int)
            self.assertEqual(data[0]['city_name'], 'Москва')

    def test_get_search_history_empty(self):
        """ Получение истории, когда она пуста """

        url = reverse(city_search_count)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(data), 0)


class HomeViewTest(TestCase):
    """ Тесты для view home """

    def setUp(self):
        self.client = Client()
        self.home_url = reverse('home')
        self.user = User.objects.create()
        self.encrypted_user_id = encrypt_user_id(str(self.user.user_id))
        self.client.cookies['user_id'] = self.encrypted_user_id

    @patch('weather_forecast.utils.request_api')
    def test_home_get_no_city(self, mock_request_api):
        """ Успешный GET запрос без параметра города (чистая стартовая страница) """
        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, 'Приветствуем! Введите название города, чтобы увидеть прогноз погоды.')
        self.assertIsNone(response.context['forecasts'])
        self.assertIsNone(response.context['error_message'])
        self.assertEqual(response.context['city_name_for_template'], '')
        self.assertIn('last_cities', response.context)
        self.assertIn('user_id', response.cookies)

    @patch('weather_forecast.utils.request_api')
    def test_home_get_with_city_success(self, mock_request_api):
        """ Успешный GET запрос с названием города в параметрах """

        mock_request_api.return_value = {'error': None, 'data': 'Тестовые данные'}
        response = self.client.get(self.home_url, {'city_name': 'Москва'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertIsNotNone(response.context['forecasts'])
        self.assertIsNone(response.context['error_message'])
        self.assertEqual(response.context['city_name_for_template'], 'Москва')
        self.assertIn('Москва', response.context['last_cities'])
        self.assertTrue(SearchHistory.objects.filter(user=self.user, city_name='Москва').exists())
        self.assertIn('user_id', response.cookies)

    @patch('weather_forecast.utils.request_api')
    def test_home_get_with_city_error(self, mock_request_api):
        """ Неуспешный GET запрос с названием города в параметрах (неверный город) """

        mock_request_api.return_value = {'error': 'Не удалось найти информацию о погоде в заданном городе', 'data': None}
        response = self.client.get(self.home_url, {'city_name': 'invalid city'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertEqual(response.context['error_message'], 'Не удалось найти информацию о погоде в заданном городе')
        self.assertIsNone(response.context['forecasts'])
        self.assertEqual(response.context['city_name_for_template'], 'invalid city')
        self.assertNotIn('InvalidCity', response.context['last_cities'])
        self.assertFalse(SearchHistory.objects.filter(user=self.user, city_name='invalid city').exists())
        self.assertIn('user_id', response.cookies)

    @patch('weather_forecast.utils.request_api')
    def test_home_post_with_city_success(self, mock_request_api):
        """ Успешный POST запрос """

        mock_request_api.return_value = {'error': None, 'data': 'Тестовые данные'}
        response = self.client.post(self.home_url, {'city_name': 'Москва'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertIsNotNone(response.context['forecasts'])
        self.assertIsNone(response.context['error_message'])
        self.assertEqual(response.context['city_name_for_template'], 'Москва')
        self.assertIn('Москва', response.context['last_cities'])
        self.assertTrue(SearchHistory.objects.filter(user=self.user, city_name='Москва').exists())
        self.assertIn('user_id', response.cookies)

    @patch('weather_forecast.utils.request_api')
    def test_home_post_with_city_error(self, mock_request_api):
        """ Неуспешный POST запрос (невалидный city_name) """

        mock_request_api.return_value = {'error': 'Не удалось найти информацию о погоде в заданном городе',
                                         'data': None}
        response = self.client.post(self.home_url, {'city_name': 'invalid city'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertIsNone(response.context['forecasts'])
        self.assertEqual(response.context['error_message'], 'Не удалось найти информацию о погоде в заданном городе')
        self.assertEqual(response.context['city_name_for_template'], 'invalid city')
        self.assertNotIn('invalid city', response.context['last_cities'])
        self.assertFalse(SearchHistory.objects.filter(user=self.user, city_name='invalid city').exists())
        self.assertIn('user_id', response.cookies)

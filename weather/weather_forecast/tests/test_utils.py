import json
import unittest

from requests.exceptions import RequestException
from unittest.mock import Mock, patch

from ..utils import (update_last_cities, get_last_cities_from_cookie,
                     decrypt_user_id, encrypt_user_id, parse_coordinates)


class TestUpdateLastCities(unittest.TestCase):
    def test_update_empty_list(self):
        """ Обновление пустого списка """

        self.assertEqual(update_last_cities([], 'Москва'), ['Москва'])

    def test_update_with_multiple_elements(self):
        """ Обновление списка с несколькими элементами """

        self.assertEqual(update_last_cities(['Москва', 'Лондон', 'Париж'], 'Токио'),
                         ['Токио', 'Москва', 'Лондон', 'Париж'])

    def test_update_with_existing_element(self):
        """ Обновление списка, содержащего элемент, который уже существует """

        self.assertEqual(update_last_cities(['Москва', 'Лондон', 'Париж'], 'Москва'), ['Москва', 'Лондон', 'Париж'])

    def test_update_list_near_limit(self):
        """ Обновление заполненного списка """

        self.assertEqual(update_last_cities(['Москва', 'Лондон', 'Париж', 'Токио', 'Берлин'], 'Рим'),
                         ['Рим', 'Москва', 'Лондон', 'Париж', 'Токио'])

    def test_update_with_empty_city_name(self):
        """ Обновление списка с пустым city_name """

        self.assertEqual(update_last_cities(['Москва', 'Лондон'], ''), ['', 'Москва', 'Лондон'])


class TestGetLastCitiesFromCookie(unittest.TestCase):
    def test_cookie_exists_and_valid_json(self):
        """ Cookie существует и содержит валидный JSON
            - пустой список
            - список с одним или несколькими городами
        """
        
        mock_request = Mock()
        mock_request.COOKIES = {'last_cities': json.dumps([])}
        self.assertEqual(get_last_cities_from_cookie(mock_request), [])

        mock_request.COOKIES = {'last_cities': json.dumps(['Москва'])}
        self.assertEqual(get_last_cities_from_cookie(mock_request), ['Москва'])

        mock_request.COOKIES = {'last_cities': json.dumps(['Москва', 'Лондон', 'Париж'])}
        self.assertEqual(get_last_cities_from_cookie(mock_request), ['Москва', 'Лондон', 'Париж'])

    def test_cookie_does_not_exist(self):
        """ Cookie не существует """

        mock_request = Mock()
        mock_request.COOKIES = {}
        self.assertEqual(get_last_cities_from_cookie(mock_request), [])

    def test_cookie_exists_but_invalid_json(self):
        """ Cookie существует, но содержит невалидный JSON (не список) """

        mock_request = Mock()
        mock_request.COOKIES = {'last_cities': 'invalid json'}
        self.assertEqual(get_last_cities_from_cookie(mock_request), [])

        mock_request = Mock()
        mock_request.COOKIES = {'last_cities': json.dumps({'city': 'Москва'})}
        self.assertEqual(get_last_cities_from_cookie(mock_request), [])


class TestEncryptDecryptUserId(unittest.TestCase):
    def test_encryption_decryption_success(self):
        """ Успешное шифрование и дешифрование """

        user_id = 'dbeb4e99704d4b02a04566b37de11fa7'
        encrypted_user_id = encrypt_user_id(user_id)
        decrypted_user_id = decrypt_user_id(encrypted_user_id)
        self.assertEqual(decrypted_user_id, user_id)


class TestParseCoordinates(unittest.TestCase):
    @patch('weather_forecast.utils.requests.get')
    def test_parse_coordinates_success(self, mock_get):
        """ Успешное получение координат """

        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = b'<a class="mw-kartographer-maplink" data-lat="55.750556" data-lon="37.6175"></a>'

        coordinates = parse_coordinates('Москва')

        self.assertEqual(coordinates, (55.750556, 37.6175))
        mock_get.assert_called_once()

    @patch('weather_forecast.utils.requests.get')
    def test_parse_coordinates_request_error(self, mock_get):
        """ Обработка ошибок при запросе (requests.exceptions.RequestException) """

        mock_get.side_effect = RequestException('Симуляция ошибки запроса')

        coordinates = parse_coordinates('Москва')

        self.assertIsNone(coordinates)

    @patch('weather_forecast.utils.requests.get')
    def test_parse_coordinates_html_parsing_error(self, mock_get):
        """Обработка ошибок при парсинге (координаты не найдены)"""

        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = b'<html><body>No coordinates here!</body></html>'

        coordinates = parse_coordinates('Москва')

        self.assertIsNone(coordinates)

    @patch('weather_forecast.utils.requests.get')
    def test_parse_coordinates_city_not_found(self, mock_get):
        """ Обработка, когда не найден запрашиваемый город """

        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = b'<div class="noarticle"></div>'

        coordinates = parse_coordinates('Не удалось координаты на странице')

        self.assertIsNone(coordinates)

    @patch('weather_forecast.utils.requests.get')
    def test_parse_coordinates_invalid_coordinate_format(self, mock_get):
        """ Обработка некорректного формата координат """

        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = b'<a class="mw-kartographer-maplink" data-lat="abc" data-lon="def"></a>'

        coordinates = parse_coordinates('Москва')

        self.assertIsNone(coordinates)

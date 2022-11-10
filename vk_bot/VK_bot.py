import requests
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

import json

from vkinder_database.models import User, UserMark, Mark
from vkinder_database.postgres_db import VKinderPostgresqlDB
from sqlalchemy.exc import OperationalError, IntegrityError


class VkBot:
    base_url = 'https://api.vk.com/method/'

    def __init__(self, bot_token, owner_token, user_id, vk_api_version='5.131'):
        self.owner_token = owner_token
        self.vk_api_version = vk_api_version
        self.params = dict(access_token=bot_token, v=vk_api_version)
        self.user_id = user_id
        self.bot_menu = {
            'начать': {'func': self._get_user_name, 'args': (), 'keyboard': self._keyboard_start},
        }

        # TODO 1: записать информацию о VK_ID пользователя бота в БД
        self._add_user_to_db()
        self.user_info = self._get_user_info_from_vk_id(user_id)
        self.peer_user_info = {}

    def _get_user_info_from_vk_id(self, user_id):
        method_url = self.base_url + 'users.get'
        method_params = {
            'user_ids': user_id,
            'fields': 'bdate, sex, city',
        }
        all_params = {**self.params, **method_params}
        response = requests.get(method_url, params=all_params).json()
        return response['response'][0]

    def _get_user_name(self):
        return self.user_info['first_name']

    def _get_peer_user_info(self, sex_id):
        self.peer_user_info['sex'] = sex_id
        self.peer_user_generator = self._find_peer()

    def _find_peer(self):
        def get_peer_users_generator():
            offset = 0
            params = {**method_params, 'offset': offset}
            while offset < 100:
                response = requests.get(method_url, params=params).json()
                next_users = response.get('response').get('items')
                offset += 20
                params = {**method_params, 'offset': offset}
                for user in next_users:
                    yield user

        method_url = self.base_url + 'users.search'
        method_params = {
            'access_token': self.owner_token,
            'v': self.vk_api_version,
            'city_id': self.user_info.get('city').get('id'),
            'sex': self.peer_user_info.get('sex'),
            'age_from': int(self.user_info.get('bdate')[-4:]) - 5,
            'age_to': int(self.user_info.get('bdate')[-4:]) + 5,
        }
        # response = requests.get(method_url, params=all_params).json()
        return get_peer_users_generator()

    def _next_friend(self):
        return next(self.peer_user_generator)

    def _add_user_to_db(self):
        db_creds_path = 'info_not_for_git/postgresql.json'
        # print('DB_creds_path:', db_creds_path)
        with open(db_creds_path) as f:
            creds = json.load(f)
        try:
            VKinder_DB = VKinderPostgresqlDB('vkinder_db', creds)
            session = VKinder_DB.new_session()
            with session:
                try:
                    VKinder_DB.add_row(session=session, model=User, data={'user_id': self.user_id})
                    session.commit()
                except IntegrityError:
                    session.rollback()
        except OperationalError as err:
            print('Ошибка подключения к БД:', err)

    @staticmethod
    def _keyboard_start():
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Мужчина', VkKeyboardColor.SECONDARY)
        keyboard.add_button('Женщина', VkKeyboardColor.SECONDARY)
        return keyboard

    def new_message(self, request):
        if request in self.bot_menu:
            action = self.bot_menu.get(request)
            message = f"Привет, {action.get('func')(*action.get('args'))}!" \
                      f" Я умею искать пары по соответствию твоего возраста и города." \
                      f" Попробуем найти пару для тебя? Напиши 'мужчина' или 'женщина' для поиска пары " \
                      f"или можно воспользоваться кнопками ниже.."

            return message
        else:
            message = "Я пока такое не умею.."
            return message

    def new_keyboard(self, request):
        if request in self.bot_menu:
            action = self.bot_menu.get(request)
            keyboard = action.get('keyboard')()
            return keyboard
        else:
            keyboard = None
            return keyboard

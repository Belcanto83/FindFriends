import requests
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

import json
from datetime import datetime

from vkinder_database.models import User, UserMark, Mark
from vkinder_database.postgres_db import VKinderPostgresqlDB
from sqlalchemy.exc import OperationalError, IntegrityError


class KeyBoardMaker:
    @staticmethod
    def _keyboard_start():
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Мужчина', VkKeyboardColor.SECONDARY)
        keyboard.add_button('Женщина', VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Избранное', VkKeyboardColor.POSITIVE)
        keyboard.add_button('Черный список', VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Начать', VkKeyboardColor.PRIMARY)
        return keyboard

    @staticmethod
    def _keyboard_find_next_peer():
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Следующий', VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('В Избранное', VkKeyboardColor.POSITIVE)
        keyboard.add_button('В Черный список', VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Избранное', VkKeyboardColor.POSITIVE)
        keyboard.add_button('Черный список', VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Начать', VkKeyboardColor.PRIMARY)
        return keyboard


class VkBot(KeyBoardMaker):
    base_url = 'https://api.vk.com/method/'

    def __init__(self, bot_token, owner_token, user_id, vk_api_version='5.131'):
        self.owner_token = owner_token
        self.vk_api_version = vk_api_version
        self.params = dict(access_token=bot_token, v=vk_api_version)
        self.user_id = user_id
        self.peer_user_info = {}

        self.bot_menu = {
            'начать': {'func': self._message_start, 'args': (), 'keyboard': self._keyboard_start},
            'мужчина': {'func': self._message_get_peer_user_info, 'args': (2,),
                        'keyboard': self._keyboard_find_next_peer},
            'женщина': {'func': self._message_get_peer_user_info, 'args': (1,),
                        'keyboard': self._keyboard_find_next_peer},
            'следующий': {'func': self._message_get_next_peer, 'args': (),
                          'keyboard': self._keyboard_find_next_peer},
        }

        # TODO 1: записать информацию о VK_ID пользователя бота в БД
        self._add_user_to_db()
        self.user_info = self._get_user_info_from_vk_id(user_id)

    def _get_user_info_from_vk_id(self, user_id):
        method_url = self.base_url + 'users.get'
        method_params = {
            'user_ids': user_id,
            'fields': 'bdate, sex, city',
        }
        all_params = {**self.params, **method_params}
        response = requests.get(method_url, params=all_params).json()
        return response['response'][0]

    def _message_start(self):
        user_name = self.user_info['first_name']
        message = f"Привет, {user_name}!" \
                  f" Я умею искать пары по соответствию твоего возраста и города." \
                  f" Попробуем найти пару для тебя? Напиши 'мужчина' или 'женщина' для поиска пары " \
                  f"или можно воспользоваться кнопками ниже..\nЧтобы начать все заново, " \
                  f"напиши 'начать' или воспользуйся кнопкой"

        return message

    def _message_get_peer_user_info(self, sex_id):
        self.peer_user_info['sex'] = sex_id
        self.peer_user_generator = self._find_peer()
        # print('Generator', list(self.peer_user_generator))
        peer_user = next(self.peer_user_generator)
        message = f"{peer_user.get('first_name')} {peer_user.get('last_name')}\n" \
                  f"https://vk.com/id{peer_user.get('id')}\n"

        return message

    def _message_get_next_peer(self):
        peer_user = next(self.peer_user_generator)
        message = f"{peer_user.get('first_name')} {peer_user.get('last_name')}\n" \
                  f"https://vk.com/id{peer_user.get('id')}\n"

        return message

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
            'age_from': (datetime.now().year - int(self.user_info.get('bdate')[-4:])) - 5,
            'age_to': (datetime.now().year - int(self.user_info.get('bdate')[-4:])) + 5,
        }
        # resp = requests.get(method_url, params=method_params).json()
        # print('Response:', resp)

        return get_peer_users_generator()

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

    def new_message(self, request):
        if request in self.bot_menu:
            action = self.bot_menu.get(request)
            message = action.get('func')(*action.get('args'))
            return message
        else:
            message = "Я пока такое не умею..\nЧтобы начать все заново, напиши 'начать'.."
            return message

    def new_keyboard(self, request):
        if request in self.bot_menu:
            action = self.bot_menu.get(request)
            keyboard = action.get('keyboard')()
            return keyboard
        else:
            keyboard = None
            return keyboard

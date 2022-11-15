import requests
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.upload import VkUpload

import json
from datetime import datetime
from io import BytesIO

from .vkinder_database import User, UserMark
from .vkinder_database import VKinderPostgresqlDB
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

    def __init__(self, bot_token, owner_token, user_id, vk_auth, vk_api_version='5.131'):
        self.vk_auth = vk_auth
        self.owner_token = owner_token
        self.bot_token = bot_token
        self.vk_api_version = vk_api_version
        self.params = dict(access_token=bot_token, v=vk_api_version)
        self.user_id = user_id
        self.peer_user_generator = None
        self.peer_user = None
        self.peer_user_info = {}

        self.bot_menu = {
            'начать': {'func': self._message_start, 'args': (),
                       'keyboard': self._keyboard_start, 'attachment': self._attachment_none},
            'мужчина': {'func': self._message_get_peer_user_info, 'args': (2,),
                        'keyboard': self._keyboard_find_next_peer, 'attachment': self._attachment_get_peer_user_photos},
            'женщина': {'func': self._message_get_peer_user_info, 'args': (1,),
                        'keyboard': self._keyboard_find_next_peer, 'attachment': self._attachment_get_peer_user_photos},
            'следующий': {'func': self._message_get_next_peer, 'args': (),
                          'keyboard': self._keyboard_find_next_peer,
                          'attachment': self._attachment_get_peer_user_photos},
            'в избранное': {'func': self._message_added_to_favorite, 'args': (1,),
                            'keyboard': self._keyboard_find_next_peer, 'attachment': self._attachment_none},
            'избранное': {'func': self._message_get_peers_by_mark, 'args': (1,),
                          'keyboard': self._keyboard_find_next_peer, 'attachment': self._attachment_none},

        }

        self.VKinder_DB = self._create_db_connection()

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
        self.peer_user = peer_user
        message = f"{peer_user.get('first_name')} {peer_user.get('last_name')}\n" \
                  f"https://vk.com/id{peer_user.get('id')}\n"

        return message

    def _message_get_next_peer(self):
        if self.peer_user_generator:
            peer_user = next(self.peer_user_generator)
            self.peer_user = peer_user
            message = f"{peer_user.get('first_name')} {peer_user.get('last_name')}\n" \
                      f"https://vk.com/id{peer_user.get('id')}\n"

            return message
        message = "Вы пока еще не выбрали критерии поиска. Пожалуйста, задайте критерии поиска " \
                  "или введите команду 'начать', чтобы начать все сначала.."
        return message

    def _message_get_peers_by_mark(self, mark):
        peer_ids = self._get_peer_users_by_mark(mark)
        if peer_ids:
            peer_users = []
            for peer_user_id in peer_ids:
                peer_user = self._get_user_info_from_vk_id(peer_user_id)
                peer_message = f"{peer_user.get('first_name')} {peer_user.get('last_name')}\n" \
                               f"https://vk.com/id{peer_user.get('id')}\n"
                peer_users.append(peer_message)
            message = '\n'.join(peer_users)
            return message
        message = "Вы пока еще никого не добавили в Избранное.. Давай начнем поиск, чтобы найти подходящих людей?"
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
            'city_id': self.user_info.get('city').get('id') if self.user_info.get('city') else 1,
            'sex': self.peer_user_info.get('sex'),
            'age_from': (datetime.now().year - int(self.user_info.get('bdate')[-4:])) - 5
            if self.user_info.get('bdate') else 20,
            'age_to': (datetime.now().year - int(self.user_info.get('bdate')[-4:])) + 5
            if self.user_info.get('bdate') else 99,
        }
        # resp = requests.get(method_url, params=method_params).json()
        # print('Response:', resp)

        return get_peer_users_generator()

    def _get_user_photos(self, album_id, photos_count):
        """Метод возвращает список фотографий пользователя (предполагаемого друга) в сети VK"""
        method_url = self.base_url + 'photos.get'
        method_params = {
            'access_token': self.owner_token,
            'v': self.vk_api_version,
            'owner_id': self.peer_user.get('id'),
            'album_id': str(album_id),
            'extended': True,
            'photo_sizes': True,
            'rev': True,
            'count': photos_count,
        }
        # peer_photos = requests.get(method_url, params=method_params).json().get('response').get('items')

        response = requests.get(method_url, params=method_params).json().get('response')
        if response:
            peer_photos = response.get('items')

            # возьмем из каждого объекта "peer_photo" только нужные нам атрибуты: url(max_size) и кол-во лайков
            peer_photos_part_info = [
                {'url': photo.get('sizes')[-1].get('url'), 'likes': photo.get('likes').get('count')}
                for photo in peer_photos]
            # отсортируем фото по кол-ву лайков
            photos_to_send = sorted(peer_photos_part_info, key=lambda itm: itm.get('likes'), reverse=True)[:3]
            return photos_to_send
        return []

    @staticmethod
    def _upload_photos(upload, photos_to_upload):
        if photos_to_upload:
            photos_urls = [photo_to_upload.get('url') for photo_to_upload in photos_to_upload]
            img_list = []
            for photo_url in photos_urls:
                img = requests.get(photo_url).content
                f = BytesIO(img)
                img_list.append(f)
            response_objects = upload.photo_messages(img_list)
            attachments = []
            for itm in response_objects:
                owner_id = itm['owner_id']
                photo_id = itm['id']
                access_key = itm['access_key']
                attachment = f"photo{owner_id}_{photo_id}_{access_key}"
                attachments.append(attachment)
            return ','.join(attachments)
        return None

    def _message_added_to_favorite(self, mark):
        if self.peer_user:
            self._add_peer_to_user_mark_table(mark)
            message = f"Позьзователь {self.peer_user.get('first_name')} {self.peer_user.get('last_name')} " \
                      f"добавлен в Избранное!"
            return message
        message = "Вы пока еще не выбрали критерии поиска.. Пожалуйста, задайте критерии поиска или введите " \
                  "команду 'начать', чтобы начать все сначала.."
        return message

    @staticmethod
    def _attachment_none():
        return None

    def _attachment_get_peer_user_photos(self):
        upload = VkUpload(self.vk_auth)
        if self.peer_user:
            peer_user_photos = self._get_user_photos('profile', 10)
            attachment = self._upload_photos(upload, peer_user_photos)
            return attachment
        return None

    def _add_user_to_db(self):
        session = self.VKinder_DB.new_session()
        with session:
            try:
                self.VKinder_DB.add_row(session=session, model=User, data={'user_id': self.user_id})
                session.commit()
            except IntegrityError:
                session.rollback()

    def _add_peer_to_user_mark_table(self, mark):
        session = self.VKinder_DB.new_session()
        with session:
            try:
                self.VKinder_DB.add_row(session=session, model=UserMark,
                                        data={
                                            'user_id': self.user_id,
                                            'marked_user_id': self.peer_user.get('id'),
                                            'mark_id': mark
                                        })
                session.commit()
            except IntegrityError:
                session.rollback()

    def _get_peer_users_by_mark(self, mark):
        session = self.VKinder_DB.new_session()
        with session:
            favorite_list = session.query(UserMark).filter(
                UserMark.user_id == self.user_id and UserMark.mark == mark).all()
            peer_ids = [row.marked_user_id for row in favorite_list]
            return peer_ids

    @staticmethod
    def _create_db_connection():
        db_creds_path = 'info_not_for_git/postgresql.json'
        with open(db_creds_path) as f:
            creds = json.load(f)
        VKinder_DB = None
        try:
            VKinder_DB = VKinderPostgresqlDB('vkinder_db', creds)
        except OperationalError as err:
            print('Ошибка подключения к БД:', err)
        return VKinder_DB

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

    def new_attachment(self, request):
        if request in self.bot_menu:
            action = self.bot_menu.get(request)
            attachment = action.get('attachment')()
            return attachment
        else:
            attachment = None
            return attachment

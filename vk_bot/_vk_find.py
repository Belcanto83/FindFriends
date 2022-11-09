import requests


# TODO 2: Подумать, стоит ли выносить поиск по VK на токене пользователя (НЕ бота!) в отдельный класс...
class VkFinder:
    base_url = 'https://api.vk.com/method/'

    def __init__(self, token, user, peer_user, vk_api_version='5.131'):
        self.params = dict(access_token=token, v=vk_api_version)
        self.user = user
        self.peer_user = peer_user

    def find_peer(self):
        def get_peer_users_generator():
            offset = 0
            params = {**all_params, 'offset': offset}
            while offset < 100:
                response = requests.get(method_url, params=params).json()
                next_users = response.get('response').get('items')
                offset += 20
                params = {**all_params, 'offset': offset}
                for user in next_users:
                    yield user

        method_url = self.base_url + 'users.search'
        method_params = {
            'city_id': self.user.get('city').get('id'),
            'sex': self.peer_user.get('sex'),
            'age_from': int(self.user.get('bdate')[-4:]) - 5,
            'age_to': int(self.user.get('bdate')[-4:]) + 5,
        }
        all_params = {**self.params, **method_params}
        return get_peer_users_generator()

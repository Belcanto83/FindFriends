# from random import randrange
#
# import json
# import vk_api.vk_api
# from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
# from vk_api.longpoll import VkLongPoll, VkEventType
# from vk_api.keyboard import VkKeyboard, VkKeyboardButton, VkKeyboardColor
#
# with open('info_not_for_git/vk_bot.json') as f:
#     data = json.load(f)
# vk_bot_token = data['token']
# print(vk_bot_token)
#
# vk = vk_api.VkApi(token=vk_bot_token)
# vk_s = vk.get_api()
# longpoll = VkBotLongPoll(vk, 216943135)
#
#
# def write_msg(user_id, message):
#     vk.method('messages.send', {'user_id': user_id, 'message': message,  'random_id': randrange(10 ** 7), })
#
#
# for event in longpoll.listen():
#     if event.type == VkBotEventType.MESSAGE_NEW:
#
#         if event.group_id:
#             request = event.text.lower()
#
#             if request == "start":
#                 write_msg(event.user_id, f"Привет, {event.user_id}")
#             elif request == "пока":
#                 write_msg(event.user_id, "Пока((")
#             else:
#                 write_msg(event.user_id, "Не понял вашего ответа...")

###################################################################################################################

import json
from random import randrange

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from vk_bot import VkBot

with open('info_not_for_git/vk_owner.json') as f:
    data = json.load(f)
owner_token = data['token']

with open('info_not_for_git/vk_bot.json') as f:
    data = json.load(f)
bot_token = data['token']

vk = vk_api.VkApi(token=bot_token)
longpoll = VkLongPoll(vk)

vk_bots = {}


def write_msg(user_id, message, keyboard=None):
    post = {
        'user_id': user_id,
        'message': message,
        'random_id': randrange(10 ** 7),
        'keyboard': keyboard.get_keyboard() if keyboard else None,
    }
    vk.method('messages.send', post)


for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:

        if event.to_me:
            vk_bot = vk_bots.get(event.user_id)
            if vk_bot is None:
                vk_bot = VkBot(bot_token, owner_token, event.user_id)
                vk_bots[event.user_id] = vk_bot

            request = event.text.lower()
            write_msg(event.user_id, vk_bot.new_message(request), vk_bot.new_keyboard(request))

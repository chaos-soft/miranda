from datetime import datetime
import collections
import html


AUTHORIZATION_ANCHOR = '<a href="{}" target="_blank">Авторизация в {}</a>.'


def print_error(messages, e):
    t = '[{}] {}'.format(str(datetime.now()).split(' ')[1][:8], e)
    print(t)
    messages.append(dict(id='m', text=t))


def str_to_list(str_):
    """Парсит строку с запятыми в массив."""
    return list(map(str.strip, str_.split(',')))


class UserList(collections.UserList):
    """
    Метод append применяет html.escape к message['text'], если message['id']
    не в config['base']['exclude_ids'].
    """

    def __init__(self, config):
        self.exclude_ids = config['base'].getlist('exclude_ids')
        super().__init__()

    def append(self, message):
        if message['id'] not in self.exclude_ids:
            message['text'] = html.escape(message['text'], quote=True)

        super().append(message)

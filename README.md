# Miranda — чат для GoodGame, Sc2tv, Twitch, YouTube и VK Play Live

Чат поддерживает донаты через GoodGame и Sc2tv.
Подписки GoodGame и Twitch.

## Установка

Получение:

    git clone https://github.com/chaos-soft/miranda.git && cd miranda

Виртуальное окружение:

    python3 -m venv venv

Зависимости:

    venv/bin/pip install --no-cache-dir --upgrade -r requirements.txt

Все настройки хранятся в файле config.ini.
Находиться он должен в ~/.config/miranda.
Там же должен быть и twitch.json.
Проще всего сделать ссылку на текущую папку:

    ln -s $(pwd) ~/.config/miranda

Запуск:

    venv/bin/python -m miranda

Либо запуск через Docker:

    docker-compose up

## Базовая настройка GoodGame и Twitch

    [goodgame]
    # Номер канала можно взять из адресной строки плеера в окне.
    channels = 22759

    [sc2tv]
    # Тут всё несколько сложнее.
    channels = 177013

    [twitch]
    # Также из адресной строки.
    channels = chaos_soft

## access_token для Twitch

Используем API для получения токена и сохраняем его в
~/.config/miranda/twitch.json.

    curl -X POST -d 'client_id=xxx&client_secret=xxx&grant_type=client_credentials&scope=chat:read' https://id.twitch.tv/oauth2/token > twitch.json

Заполните client_id и client_secret перед выполнением запроса.

## Настройка Яндекс-бабы (устарело)

Сперва необходимо получить [API-ключ](https://tech.yandex.ru/speechkit/jsapi/)
для использования данного сервиса.
Затем прописать его в tts_api_key, что в config.ini.
Должно получиться следующее:

    tts_api_key = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

## Оформление и темы

Интерфейс был полностью удалён.
Смотрите [miranda-react](https://github.com/chaos-soft/miranda-react).

## Релизы

Все master-коммиты являются стабильными версиями.

## Руководство по стилю

В проекте используются mypy и Flake8. Настройки для Flake8:

    "--ignore=D100,D101,D102,D103,D104,D105,D106,D107",
    "--max-line-length=119"

## GoodGame
## Playwright
## Sc2tv
## Twitch
## Команды
## Описание остальных параметров config.ini

v1

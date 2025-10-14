# Miranda — чат для GoodGame, Twitch, VK и YouTube

Чат поддерживает донаты через GoodGame.
Подписки GoodGame и Twitch.
Показывает статистику со всех порталов.

## Установка

Получение:

    git clone https://github.com/chaos-soft/miranda.git

Виртуальное окружение:

    python3 -m venv venv

Установка:

    venv/bin/pip install --no-cache-dir --upgrade -e ./miranda

Все настройки хранятся в файле config.ini.
Находиться он должен в ~/.config/miranda.
Получить версию по умолчанию можно командой:

    mkdir -p ~/.config/miranda && curl -LJ -o ~/.config/miranda/config.ini https://github.com/chaos-soft/miranda/raw/refs/heads/master/config.ini

Запуск:

    venv/bin/python -m miranda

Либо запуск через Docker:

    docker compose up

## Базовая настройка (config.ini)

    [goodgame]
    # Номер канала можно взять из адресной строки плеера в окне.
    channels = 22759

    [twitch]
    # Также из адресной строки.
    channels = chaos_soft

    [vkplay]
    # Также из адресной строки.
    channel = chaos-soft

    [youtube]
    # Идентификатор канала.
    channel = UCfAAPj3rJwMW1D9ts0jtx9g

## Авторизация

Для корректной работы всех порталов необходимо авторизоваться на каждом из них.
После запуска чата в [главном интерфейсе](http://localhost:5173/#/main)
появятся ссылки для авторизации.
После предоставления прав будет произведено перенаправление на
http://localhost:5173.
В адресной строке будет указан code,
который нужно скопировать в config.ini к соответствующему сайту.
Страницу можно закрыть.

### YouTube

Для YouTube требуется наличие файла client_secret.json для доступа к API.
Предоставить его со стороны разработчика невозможно по нескольким причинам.
Одна из них — ограничение по квоте в 10000 в день.
Модуль настроен так, чтобы он мог работать на протяжении восьми часов.
То есть сообщения из чата забираются раз в 15 секунд,
а статистика обновляется раз в 10 минут.

Получить client_secret.json можно в
[Google Developers Console](https://console.developers.google.com/).

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

В проекте используются mypy и Flake8.
Настройки для Flake8:

    "--ignore=D100,D101,D102,D103,D104,D105,D106,D107",
    "--max-line-length=119"

## GoodGame
## Twitch
## VK
## YouTube
## YouTube Playwright
## Команды
## Описание остальных параметров config.ini

v1

# Habit Tracker

Backend SPA-приложения для управления полезными привычками
с напоминаниями в Telegram.

## Возможности

- Регистрация и вход по email.
- JWT-аутентификация.
- Создание, просмотр, изменение и удаление своих привычек.
- Просмотр публичных привычек.
- Проверка ограничений привычек.
- Пагинация LimitOffsetPagination: 5 записей по умолчанию,
  максимум 20 за запрос.
- Напоминания в Telegram через Celery и Redis.
- Документация API: Swagger и ReDoc.

## Технологии

Python, Django, Django REST Framework, PostgreSQL,
Simple JWT, Celery, Redis, Poetry, drf-spectacular.

Точные версии зависимостей зафиксированы в poetry.lock.

## Установка

Требуются Python 3.14, Poetry, PostgreSQL.
Для запуска Redis в контейнере требуется Docker.

```powershell
git clone https://github.com/dimonchik2005/habit_tracker.git
cd habit_tracker
git switch feature/habit-tracker
poetry install
```

## Настройка окружения

Создайте PostgreSQL-базу habit_tracker.

Скопируйте шаблон настроек:

```powershell
Copy-Item .env.template .env
```

Заполните .env своими значениями:
секретным ключом Django, параметрами PostgreSQL,
токеном Telegram-бота и адресами Redis.

Файл .env не должен попадать в Git.

Примените миграции:

```powershell
poetry run python manage.py migrate
```

## Запуск Django

```powershell
poetry run python manage.py runserver
```

Документация:

- Swagger: http://127.0.0.1:8000/api/docs/
- ReDoc: http://127.0.0.1:8000/api/redoc/
- OpenAPI: http://127.0.0.1:8000/api/schema/

## Основные эндпоинты

| Метод | Адрес | Назначение |
|---|---|---|
| POST | /api/users/register/ | Регистрация |
| POST | /api/token/ | Получение access и refresh |
| POST | /api/token/refresh/ | Обновление access |
| GET, POST | /api/habits/ | Список своих привычек и создание |
| GET, PUT, PATCH, DELETE | /api/habits/{id}/ | Работа со своей привычкой |
| GET | /api/habits/public/ | Публичные привычки |

Для защищённых запросов передавайте заголовок:

```text
Authorization: Bearer <access_token>
```

Пример пагинации:

```text
/api/habits/?limit=5&offset=0
```

## Правила привычек

- Продолжительность: от 1 до 120 секунд.
- Периодичность: от 1 до 7 дней.
- Нельзя одновременно указать награду и связанную привычку.
- Связанная привычка должна быть своей и приятной.
- Приятная привычка не может иметь награду или связанную привычку.
- Нельзя убрать признак приятной привычки,
  пока она используется как награда.

## Подключение Telegram

1. Создайте бота через @BotFather.
2. Укажите его токен в TELEGRAM_BOT_TOKEN в .env.
3. Откройте своего бота и отправьте /start.
4. Получите ID своего личного чата через Telegram Bot API getUpdates.
5. Запишите ID в telegram_chat_id своего пользователя
   через Django shell.

```powershell
poetry run python manage.py shell
```

```python
from users.models import User

user = User.objects.get(email="email_зарегистрированного_пользователя")
user.telegram_chat_id = 123456789  # Замените своим Chat ID.
user.save(update_fields=["telegram_chat_id"])
```

Выход из shell:

```python
exit()
```

## Redis и Celery

Первое создание Redis-контейнера:

```powershell
docker run -d --name habit-redis -p 127.0.0.1:6379:6379 redis:7-alpine
```

При последующих запусках:

```powershell
docker start habit-redis
```

Проверка Redis:

```powershell
docker exec habit-redis redis-cli ping
```

В отдельном терминале запустите Worker.
Для локальной разработки на Windows используется solo:

```powershell
poetry run celery -A config worker --loglevel=INFO --pool=solo
```

В другом терминале запустите один экземпляр Beat:

```powershell
poetry run celery -A config beat --loglevel=INFO
```

Beat ставит задачу в очередь каждую минуту.
Worker отправляет напоминания о полезных привычках,
время которых наступило и периодичность которых соблюдена.

Django и Celery используют общий часовой пояс из TIME_ZONE.

После простоя отправляется одно актуальное напоминание
после наступления сегодняшнего времени. Сообщения
за каждый пропущенный день отдельно не отправляются.

Следующий интервал отсчитывается от успешной отправки.
При ошибке отправки задача повторяет попытку
при следующем запуске.

Блокировка записи защищает от одновременной обработки.
При сбое после доставки сообщения, но до сохранения
результата в базе повторная отправка всё ещё возможна.

## Проверки

```powershell
poetry run python manage.py check
poetry run python manage.py makemigrations --check --dry-run
poetry run python manage.py spectacular --file schema.yml --validate
poetry run coverage run manage.py test
poetry run coverage report --fail-under=80
```

HTML-отчёт покрытия:

```powershell
poetry run coverage html
```

Откройте htmlcov/index.html.

Тесты используют отдельную тестовую базу PostgreSQL.
Пользователю БД требуется право её создания.
Telegram API в тестах подменяется mock-объектами.

## Ветки

Разработка ведётся в feature/habit-tracker.
Курсовая передаётся через Pull Request в develop.
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

## Запуск через Docker Compose

Требуются Docker и Docker Compose. На Windows должен быть запущен
Docker Desktop в режиме Linux-контейнеров.

Конфигурация Docker находится в ветке `feature/docker-deploy`.

Создайте `.env` из шаблона, если файл ещё не создан:

```powershell
Copy-Item .env.template .env
```

Заполните настройки PostgreSQL, SECRET_KEY и TELEGRAM_BOT_TOKEN.
Для локального запуска укажите:

```dotenv
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Compose автоматически задаёт контейнерам адрес PostgreSQL `db`,
адрес брокера `redis://redis:6379/0`
и backend результатов `redis://redis:6379/1`.

Проверка конфигурации и запуск:

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps -a
```

### Сервисы

| Сервис | Назначение |
|---|---|
| db | PostgreSQL |
| redis | Очередь задач и результаты Celery |
| migrate | Миграции и сбор статики |
| web | Django через Gunicorn |
| worker | Выполнение задач Celery |
| beat | Запуск задач по расписанию |
| nginx | Приём HTTP-запросов и выдача статики |

Перед миграциями Compose ожидает готовности PostgreSQL.
Приложение и Celery запускаются после успешного завершения `migrate`.

Состояние `Exited (0)` у `migrate` — нормальное:
сервис выполнил работу и завершился.

Наружу опубликован только порт 80 Nginx.
Остальные сервисы доступны внутри сети Compose.

### Адреса локального приложения

- Swagger: http://localhost/api/docs/
- ReDoc: http://localhost/api/redoc/
- Админка: http://localhost/admin/

Создание администратора:

```powershell
docker compose exec web python manage.py createsuperuser
```

База в Docker отдельная: пользователи и привычки из локального
PostgreSQL автоматически в неё не переносятся.

### Данные и управление контейнерами

Используются именованные volumes:

- postgres_data — данные PostgreSQL;
- redis_data — данные Redis;
- static_data — собранная статика;
- beat_data — состояние расписания Celery Beat.

Просмотр логов:

```powershell
docker compose logs --tail=50 web nginx
docker compose logs --tail=50 worker beat
docker compose logs --tail=50 migrate
```

Остановка и повторный запуск:

```powershell
docker compose stop
docker compose start
```

Удаление контейнеров с сохранением данных:

```powershell
docker compose down
```

Не используйте `docker compose down -v` для обычной остановки:
флаг `-v` удаляет volumes вместе с данными.
Volumes не заменяют резервные копии.

### Тесты и линтер

Запуск тестов в контейнере:

```powershell
docker compose exec web python manage.py test
```

Ruff запускается в локальном Poetry-окружении:

```powershell
poetry install --with dev
poetry run ruff check .
```

В Docker-образ устанавливаются только основные зависимости,
поэтому Ruff и coverage в нём отсутствуют.

### Telegram при запуске в Docker

Worker и Beat запускаются через Compose автоматически.
Отдельные команды запуска Celery выполнять не нужно.

Для привязки Chat ID откройте Django shell:

```powershell
docker compose exec web python manage.py shell
```

Далее используйте код из раздела «Подключение Telegram».

После изменения токена в `.env` пересоздайте соответствующие контейнеры:

```powershell
docker compose up -d --no-build web worker beat
```

Обычный `restart` не обновляет переменные окружения контейнера.

При проверке серверных напоминаний остановите локальные
Worker и Beat, если они используют того же бота:

```powershell
docker compose stop beat worker
```

## GitHub Actions и автоматический деплой

Workflow расположен в `.github/workflows/ci.yml`.

Проверки запускаются:

- при push в main, develop и feature/docker-deploy;
- при Pull Request в main и develop.

Последовательно выполняются:

1. Установка Python и зависимостей Poetry.
2. Тесты с отдельными PostgreSQL и Redis.
3. Проверка Ruff.
4. Сборка Docker-образа.
5. Деплой — только при push в feature/docker-deploy.

При ошибке последующие шаги не выполняются.
Группа concurrency предотвращает одновременные запуски workflow.

Образ собирается на GitHub, передаётся на сервер через SCP
и загружается в Docker. Вместе с ним передаются Compose
и конфигурация Nginx. Серверный `.env` не перезаписывается.

На сервере выполняется:

```bash
docker compose up -d --no-build --force-recreate --wait --wait-timeout 180
```

Затем workflow проверяет HTTP-ответ `/admin/login/`.

При обновлении возможен небольшой перерыв в работе.
Именованные volumes сохраняются. Автоматический откат не настроен.

### GitHub Secrets

В Settings → Secrets and variables → Actions необходимо добавить:

| Секрет | Назначение |
|---|---|
| SSH_HOST | Публичный IP сервера |
| SSH_USER | Пользователь для SSH-подключения |
| SSH_PRIVATE_KEY | Приватный SSH-ключ деплоя |
| SSH_KNOWN_HOSTS | Проверенный публичный ключ сервера в формате known_hosts |

Публичная часть ключа деплоя должна быть добавлена
в `~/.ssh/authorized_keys` серверного пользователя.

Workflow проверяет ключ сервера через StrictHostKeyChecking.
Приватные ключи и настоящие пароли в репозиторий не добавляются.

### Подготовка сервера

Используется ВМ Yandex Cloud с Ubuntu 24.04 LTS.

На сервере должны быть установлены Docker Engine и Compose.
Пользователь деплоя должен иметь доступ к Docker
без интерактивного запроса sudo.

Docker должен запускаться вместе с системой:

```bash
sudo systemctl enable --now docker
```

Создайте каталог проекта и серверный `.env`:

```bash
mkdir -p ~/habit_tracker
chmod 700 ~/habit_tracker
cd ~/habit_tracker
umask 077
nano .env
```

Заполните переменные по `.env.template`, используя отдельные
секретный ключ Django и пароль базы данных.

Для текущего сервера:

```dotenv
DEBUG=False
ALLOWED_HOSTS=51.250.103.23,localhost,127.0.0.1
DATABASE_HOST=db
DATABASE_PORT=5432
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
TIME_ZONE=Europe/Moscow
CORS_ALLOWED_ORIGINS=
```

Также обязательно заполните SECRET_KEY, DATABASE_NAME,
DATABASE_USER, DATABASE_PASSWORD и токен Telegram для напоминаний.

Ограничьте доступ к файлу:

```bash
chmod 600 .env
```

Сеть ВМ должна разрешать SSH для деплоя и HTTP на порту 80.
Порты PostgreSQL и Redis наружу не открываются.

После первого деплоя создайте администратора серверной базы:

```bash
cd ~/habit_tracker
docker compose exec web python manage.py createsuperuser
```

### Адреса серверного приложения

- Swagger: http://51.250.103.23/api/docs/
- ReDoc: http://51.250.103.23/api/redoc/
- Админка: http://51.250.103.23/admin/

Текущее учебное развёртывание работает по HTTP.
Для использования с реальными пользовательскими данными требуется HTTPS.

При смене IP необходимо обновить настройки доступа,
SSH_HOST, SSH_KNOWN_HOSTS и адреса в документации.

### Ветка Docker и деплоя

Изменения этого ДЗ находятся в `feature/docker-deploy`.
Pull Request создаётся из `feature/docker-deploy` в `develop`.

В текущем workflow слияние в develop запускает проверки,
но не деплой. Для переноса деплоя на develop нужно изменить
условия `if` у шагов настройки SSH, передачи файлов и деплоя.
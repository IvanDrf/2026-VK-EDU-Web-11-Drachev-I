# 2026-VK-EDU-Web-11-Drachev-I

### Для запуска через Docker:

1) Создайте .env

```bash
cat .env.example > .env
```

2) Запустите docker-compose

```bash
docker-compose up -d
```

---

### Для локального запуска:

1) Python >= 3.12

2) Установите зависимости

```bash
pip install -r requirements.txt
```


3) Создайте .env

```bash
cat .env.example > .env
``` 

4) Запустите приложение

```bash
python manage.py runserver
```
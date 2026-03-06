# celery_worker.py
from app.main import celery_app

if __name__ == '__main__':
    celery_app.start()
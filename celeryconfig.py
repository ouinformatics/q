import config

BROKER_URL = config.BROKER_URL

CELERY_SEND_EVENTS = True
CELERY_TASK_RESULT_EXPIRES = None

CELERY_RESULT_BACKEND = config.CELERY_RESULT_BACKEND

CELERY_MONGODB_BACKEND_SETTINGS = config.CELERY_MONGODB_BACKEND_SETTINGS 

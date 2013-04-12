
MEMCACHE_HOST="127.0.0.1"
MEMCACHE_PORT=11211

MONGO_HOST="localhost"
MONGO_PORT="27017"
MONGO_DB="taskqueue"
MONGO_LOG_COLLECTION="tasklog"
MONGO_TOMBSTONE_COLLECTION="tombstones"

BROKER_URL = "pyamqp://someuser:somepassword@somehost.somedomain.com:5672/somevhost"
CELERY_RESULT_BACKEND = "mongodb"
CELERY_MONGODB_BACKEND_SETTINGS = {
    "host": MONGO_HOST,
    "database": MONGO_DB,
    "taskmeta_collection": MONGO_TOMBSTONE_COLLECTION
}


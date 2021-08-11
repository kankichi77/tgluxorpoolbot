import redis

class DB:
    db = None

    def __init__(self):
        self.db = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

    def set(
            self,
            key: str = None,
            value: str = None,
            ):
        return self.db.set(key, value)

    def get(
            self,
            key,
            ):
        return self.db.get(key)

    def exists(
            self,
            key,
            ):
        return self.db.exists(key)


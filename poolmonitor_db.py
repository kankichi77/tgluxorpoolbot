import redis
import configparser

class DB:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('.config')
        self.db = redis.Redis(
                host='localhost', 
                port=6379, 
                db= self.config['BOT']['Redis-DB'], 
                decode_responses=True)

    def set(
            self,
            key,
            value,
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


from poolmonitor_db import DB
import json

class PoolInfo():
    db = DB()

    def __init__(
            self,
            tgUser,
            ):
        self.tgUser = tgUser
        self.pools =[] 

    def pool(
            self,
            pool,
            uname: str = None,
            apikey: str = None,
            ):
        p = {
                "pool" : pool,
                "uname" : uname,
                "apikey" : apikey
                }
        i = self.getPool(self.pools,pool,uname)
        if i == -1:
            self.pools.append(p)
        else:
            self.pools[i]["uname"] = uname
            self.pools[i]["apikey"] = apikey

    def getPool(
            self,
            poolsList,
            pool,
            uname = None,
            apikey = None
            ):
        for i, p in enumerate(poolsList):
            if pool == p["pool"] and uname == p["uname"]:
                return i
        return -1

    def cleanUpPoolsList(self, oldPoolsList):
        old = oldPoolsList
        new = []
        for p in old:
            if self.getPool(new, p['pool'], p['uname']) == -1:
                new.append(p)
        return new

    def validate(self) -> bool:
        if not self.tgUser:
            return False
        return True

    def toJsonStr(self):
        return json.dumps(self.pools)

    def fromJsonStr(self, jsonStr):
         return json.loads(jsonStr)

    def makeDbKey(self):
        return 'poolinfo_for_' + self.tgUser

    def save(self):
        new = []
        key = self.makeDbKey()
        if self.validate():
            if self.db.exists(key):
                s = self.fromJsonStr(self.db.get(key))
                if s:
                    for p in self.pools:
                        i = self.getPool(s, p['pool'], p['uname'])
                        if i == -1:
                            new.append(p)
                        else:
                            s[i]["apikey"] = p["apikey"]
                else:
                    s = []
                    new = self.pools
            else:
                s = []
                new = self.pools
            
            s = s + new
            self.db.set(key, json.dumps(s))

    def load(self):
        key = self.makeDbKey()
        if self.db.exists(key):
            self.pools = []
            self.pools = self.fromJsonStr(self.db.get(key))


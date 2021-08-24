import logging
from poolmonitor_db import DB
import configparser
from poolinfo import PoolInfo
from datetime import datetime
from urllib import request
import json

config = configparser.ConfigParser()
config.read('.config')

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class PoolMonitor_F2():
    db = DB()

    def __init__(
            self,
            poolinfo,
            ):
        config = configparser.ConfigParser()
        config.read('.config')
        self.pooldata = None
        self.poolinfo = poolinfo

    def fetchPoolData(
            self,
            ):
        if not self.poolinfo:
            self.pooldata = None
            return
        uname = self.poolinfo["uname"]
        apiEndPoint = config["F2"]["ApiEndPoint"] + uname
        self.pooldata = json.loads(urllib.request.urlopen(apiEndPoint).read())

    def getStatusMessage(
            self,
            poolInfo,
            ):
        try:
            self.fetchPoolData()
            currendHashrate = self.getCurrentHashrate()
            total = self.getNumberOfWorkers()
            online = self.getNumberOfOnlineWorkers()
            self.resetPoolData()
        except:
            logger.info("Error retrieving Data from F2 Pool")
            raise
        try:
            self.saveNumberOfOfflineWorkers(offline)
        except:
            logger.info("Error saving Number of Offline Workers to database")
            raise
        m = []
        m.append('Latest Worker Hashrate: ' + currentHashrate)
        m.append(str(online) + '/' + str(total) + ' Workers Online')
        msg = "\n".join(m).join(['\n', '\n'])
        return msg

    def getCurrentHashrate(
            self,
            unit = None,
            ):
        if not self.pooldata:
            self.fetchPoolData()
        if self.pooldata:
            hashrate = float(self.pooldata["hashrate"]) / 1000000000000
            result = "{:0.2f}".format(hashrate) + ' TH'
        else:
            result = ""
        return result

    def get24HrHashrate(
            self,
            unit = None,
            ):
        if not self.pooldata:
            self.fetchPoolData()
        if self.pooldata:
            hashrate = float(self.pooldata["hashrate_last_day"]) / 1000000000000
            result = "{:0.2f}".format(hashrate) + ' TH'
        else:
            result = ""
        return result

    def getNumberOfWorkers(
            self,
            ):
        if not self.pooldata:
            self.fetchPoolData()
        if self.pooldata:
            result = int(self.pooldata["worker_length"])
        else:
            result = 0
        return result
        
    def getNumberOfOnlineWorkers(
            self,
            ):
        if not self.pooldata:
            self.fetchPoolData()
        if self.pooldata:
            result = int(self.pooldata["worker_length_online"])
        else:
            result = 0
        return result

    def getNumberOfOfflineWorkers(
            self,
            ):
        total = self.getNumberOfWorkers()
        online = self.getNumberOfOnlineWorkers()
        return total - online

    def resetPoolData(
            self,
            ):
        self.pooldata = None

    def getSecondsUntilNextUpdate(
            self,
            ):
        return 0

    def saveNumberOfOfflineWorkers(
            self,
            numberOfOfflineWorkers,
            ):
        key = 'numberOfOfflineWorkers_' + self.poolinfo['pool'] + '_' + self.poolinfo['uname']
        self.db.set(key, numberOfOfflineWorkers)

    def loadNumberOfOfflineWorkers(
            self,
            ):
        key = 'numberOfOfflineWorkers_' + self.poolinfo['pool'] + '_' + self.poolinfo['uname']
        if self.db.exists(key):
            return self.db.get(key)
        else:
            return -1


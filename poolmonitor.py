import logging
from poolmonitor_db import DB
from luxor import API as API_LUXOR
import configparser
from poolinfo import PoolInfo
from datetime import datetime

config = configparser.ConfigParser()
config.read('.config')

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class PoolMonitor():
    def __init__(
            self,
            tgUsername,
            poolinfo = None,
            ):
        self.tgUsername = tgUsername
        #poolinfo = PoolInfo(tgUsername)
        #poolinfo.load()
        #if poolinfo:
        #    self.setPoolInfo(poolinfo)

    def setPoolInfo(
            self,
            poolinfo,
            ):
        if poolinfo['pool'].upper() == 'LUXOR':
            self.pool = PoolMonitor_Luxor(poolinfo)
        if poolinfo['pool'].upper() == 'F2':
            self.pool = PoolMonitor_F2(poolinfo)

    def getCurrentHashrate(
            self,
            unit = None,
            ):
        return self.pool.getCurrentHashrate(unit)

    def getNumberOfOnlineWorkers(
            self,
            ):
        return self.pool.getNumberOfOnlineWorkers()

    def getNumberOfOfflineWorkers(
            self,
            ):
        #return int(self.pool.db.get("off"))  # DEBUG
        return self.pool.getNumberOfOfflineWorkers()

    def saveNumberOfOfflineWorkers(
            self,
            numberOfOfflineWorkers,
            ):
        self.pool.saveNumberOfOfflineWorkers(numberOfOfflineWorkers)

    def loadNumberOfOfflineWorkers(
            self,
            ):
        return self.pool.loadNumberOfOfflineWorkers()

    def getStatusMessage(
            self,
            tgUsername = None,
            ):
        if tgUsername:
            self.tgUsername = tgUsername

        logger.info("BEGIN: getStatusMessage(): tgusername: %s", self.tgUsername)
        poolinfo = PoolInfo(self.tgUsername)
        poolinfo.load()
        msg = ''
        if poolinfo.pools:
            m = []
            for p in poolinfo.pools:
                apiEndPoint = config['LUXOR']['ApiEndPoint']
                apiKey = p['apikey']
                pooluser = p['uname']
                self.setPoolInfo(p)
                try:
                    logger.info("Accessing %s API for user %s ...", p['pool'], pooluser)
                    try:
                        currentHashrate =  self.getCurrentHashrate('TH')
                    except:
                        logger.info("Error retrieving Current Hashrate")
                    try:
                        online = self.getNumberOfOnlineWorkers()
                    except:
                        logger.info("Error retrieving Number of Online Workers.")
                    try:
                        offline = self.getNumberOfOfflineWorkers()
                    except:
                        logger.info("Error retrieving Number Of Offline Workers.")
                    logger.info("Successfully retrieved %s API data for user %s.", p['pool'], pooluser)

                    try:
                        self.saveNumberOfOfflineWorkers(offline)
                    except:
                        logger.info("Error saving Number of Offline Workers to database")
                    total = online + offline
                    m.append('Latest Worker Hashrate: ' + currentHashrate)
                    m.append(str(online) + '/' + str(total) + ' Workers Online')
                    msg = "\n".join(m).join(['\n', '\n'])
                except:
                    msg = "Error retrieving data from the Pool."
        else:
            msg = "Please set pool information first by using the /start command.\n"
        logger.info("END: getStatusMessage()")
        return msg

    def checkOnOfflineStatus(
            self,
            tgUsername,
            init,
            ):
        """Send the alarm message."""
        init_flag = init
        poolinfo = PoolInfo(tgUsername)
        poolinfo.load()
        msg = ''
        plural = ''
        if poolinfo.pools:
            for p in poolinfo.pools:
                apiEndPoint = config['LUXOR']['ApiEndPoint']
                apiKey = p['apikey']
                pooluser = p['uname']
                poolname = p['pool']
                self.setPoolInfo(p)
                #poolmonitor = PoolMonitor(p)
                try:
                    #logger.info("Accessing %s API for user %s ...", poolname, pooluser)
                    offlineWorkers = int(self.getNumberOfOfflineWorkers())
                    #logger.info("offlineWorkers: %s %s", offlineWorkers, type(offlineWorkers))
                    if init_flag == 1:
                        prev = 0
                    else:
                        prev = int(self.loadNumberOfOfflineWorkers())
                    #logger.info("pool: %s uname: %s", poolmonitor.pool.poolinfo['pool'], poolmonitor.pool.poolinfo['uname'])
                    #logger.info("prev: %s %s", prev, type(prev))
                    logger.info("Offline Workers: prev: %s / now: %s", prev, offlineWorkers)
                    if prev != -1:
                        if offlineWorkers > 0 and offlineWorkers != prev:
                            if offlineWorkers > 1:
                                plural = 'S'
                            msg += str(offlineWorkers) + " WORKER" + plural + " OFFLINE\n"
                            #msg += "Pool: " + poolname + "  Username: " + pooluser + "\n"
                        if offlineWorkers == 0 and offlineWorkers != prev:
                            msg += "All workers are back online."
                        #logger.info("Successfully retrieved %s API data for user %s.", poolname, pooluser)
                    self.saveNumberOfOfflineWorkers(offlineWorkers)
                except:
                    logger.info("ERROR: Error in checkOnOfflineStatus() for user %s", tgUsername)
        return msg

class PoolMonitor_Luxor():
    def __init__(
            self,
            poolinfo,
            ):
        config = configparser.ConfigParser()
        config.read('.config')
        self.db = DB()
        apiEndPoint = config['LUXOR']['ApiEndPoint']
        apiKey = poolinfo['apikey']
        self.poolinfo = poolinfo
        self.api = API_LUXOR(host = apiEndPoint, method = 'POST', org = 'luxor', key = apiKey)

    def getCurrentHashrate(
            self,
            unit = None,
            ):
        m = ''
        #wk_details1H = self.api.get_worker_details_1H(self.poolinfo['uname'],'BTC',10)
        #latest_worker_hashrate = wk_details1H['data']['miners']['edges'][0]['node']['details1H']['hashrate']

        subaccts = self.api.get_subaccounts(10)
        subs = []
        latest_worker_hashrate = 0
        for s in subaccts['data']['users']['edges']:
            subs.append(s['node']['username'])
        for s in subs:
            wk_details1H = self.api.get_worker_details_1H(s,'BTC',10)
            for e in wk_details1H['data']['miners']['edges']:
                status = e['node']['details1H']['status']
                if status == 'Active':
                    latest_worker_hashrate += float(e['node']['details1H']['hashrate'])
        if unit == 'TH':
            latest_worker_hashrate = latest_worker_hashrate/1000000000000
            m = "{:.2f}".format(latest_worker_hashrate) + ' TH'
        else:
            m = latest_worker_hashrate
        return m

    def getNumberOfOnlineWorkers(
            self,
            ):
        prof_act_wk_count = self.api.get_profile_active_worker_count('BTC')
        return int(prof_act_wk_count['data']['getProfileActiveWorkers'])
        
    def getNumberOfOfflineWorkers(
            self,
            ):
        prof_inact_wk_count = self.api.get_profile_inactive_worker_count('BTC')
        return int(prof_inact_wk_count['data']['getProfileInactiveWorkers'])

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

class PoolMonitor_F2():
    db = DB()

    def __init__(
            self,
            ):
        config = configparser.ConfigParser()
        config.read('.config')

    def getCurrentHashrate(
            self,
            unit = None,
            ):
        pass

    def getNumberOfOnlineWorkers(
            self,
            ):
        pass

    def getNumberOfOfflineWorkers(
            self,
            ):
        pass

    def getSecondsUntilNextUpdate(
            self,
            ):
        return 0

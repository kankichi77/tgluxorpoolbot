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

    def getStatusMessage(
            self,
            poolinfo,
            ):
        try:
            currentHashrate =  self.getCurrentHashrate('TH')
        except:
            logger.info("Error retrieving Current Hashrate")
            raise

        try:
            online = self.getNumberOfOnlineWorkers()
        except:
            logger.info("Error retrieving Number of Online Workers.")
            raise
        try:
            offline = self.getNumberOfOfflineWorkers()
        except:
            logger.info("Error retrieving Number Of Offline Workers.")
            raise
        try:
            self.saveNumberOfOfflineWorkers(offline)
        except:
            logger.info("Error saving Number of Offline Workers to database")
            raise
        total = online + offline
        m = []
        m.append('Latest Worker Hashrate: ' + currentHashrate)
        m.append(str(online) + '/' + str(total) + ' Workers Online')
        msg = "\n".join(m).join(['\n', '\n'])
        return msg

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


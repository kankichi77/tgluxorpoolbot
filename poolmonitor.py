from luxor import API as API_LUXOR
import configparser

class PoolMonitor():

    def __init__(
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
        return self.pool.getNumberOfOfflineWorkers()

class PoolMonitor_Luxor():

    def __init__(
            self,
            poolinfo,
            ):
        config = configparser.ConfigParser()
        config.read('.config')
        apiEndPoint = config['LUXOR']['ApiEndPoint']
        apiKey = poolinfo['apikey']
        self.poolinfo = poolinfo
        self.api = API_LUXOR(host = apiEndPoint, method = 'POST', org = 'luxor', key = apiKey)

    def getCurrentHashrate(
            self,
            unit = None,
            ):
        wk_details1H = self.api.get_worker_details_1H(self.poolinfo['uname'],'BTC',10)
        latest_worker_hashrate = wk_details1H['data']['miners']['edges'][0]['node']['details1H']['hashrate']
        if unit == 'TH':
            latest_worker_hashrate = float(latest_worker_hashrate)/1000000000000
            s = "{:.2f}".format(latest_worker_hashrate) + ' TH'
        else:
            s = latest_worker_hashrate
        return s

    def getNumberOfOnlineWorkers(
            self,
            ):
        prof_act_wk_count = self.api.get_profile_active_worker_count('BTC')
        return prof_act_wk_count['data']['getProfileActiveWorkers']

    def getNumberOfOfflineWorkers(
            self,
            ):
        prof_inact_wk_count = self.api.get_profile_inactive_worker_count('BTC')
        return prof_inact_wk_count['data']['getProfileInactiveWorkers']
        
class PoolMonitor_F2():

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

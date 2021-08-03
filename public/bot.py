import requests
import configparser

config = configparser.ConfigParser()
config.read('luxorpoolbot.config')

url = 'https://api.telegram.org/bot' + config['TELEGRAM']['ApiKey'] + '/sendMessage?chat_id=928455104&text=hello'
requests.get(url)

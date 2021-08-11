import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
        Updater,
        CommandHandler,
        MessageHandler,
        Filters,
        ConversationHandler,
        CallbackContext,
        )
from poolinfo import PoolInfo
from luxor import API
import configparser

config = configparser.ConfigParser()
config.read('.config')

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SELECTMININGPOOL, SETPOOLUSERNAME, SETAPIKEY = range(3)

def start(update: Update, context: CallbackContext) -> int:
    """Starts the bot and asks the user for the Mining Pool."""
    reply_keyboard = [['Luxor']]
    update.message.reply_text(
            'Welcome to the Mining Pool Monitor Bot.\n'
            'Use the /cancel command to stop me.\n\n'
            'Please select your mining pool:',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder='Mining Pool'
                ),
            )
    return SELECTMININGPOOL

def selectMiningPool(update: Update, context: CallbackContext) -> int:
    """Stores the selected mining pool and asks for the pool username."""
    tgUser = update.message.from_user
    poolname = update.message.text
    context.user_data['poolname'] = poolname
    logger.info("Mining Pool selected for %s: %s", tgUser.username, poolname)
    update.message.reply_text(
            'Now please tell me the username for that Mining Poool.',
            reply_markup=ReplyKeyboardRemove(),
            )
    return SETPOOLUSERNAME

def setPoolUsername(update: Update, context: CallbackContext) -> int:
    """Stores the Mining Pool Username and asks for the API Key."""
    tgUser = update.message.from_user
    poolUsername = update.message.text
    poolname = context.user_data['poolname']
    context.user_data['poolUsername'] = poolUsername
    logger.info("Mining Pool Username for %s: %s", tgUser.username, poolUsername)
    update.message.reply_text(
            f'Mining Pool: {poolname}\n'
            f'Pool Username: {poolUsername}\n'
            'Now please enter the API Key for this Pool account.\n'
            'Enter /skip if this pool does not require an API Key.'
            )
    return SETAPIKEY

def setApiKey(update: Update, context: CallbackContext) -> int:
    """Stores the API Key"""
    tgUser = update.message.from_user
    apiKey = update.message.text
    logger.info("API Key for %s is set.", tgUser.username)
    poolinfo = PoolInfo(tgUser.username)
    poolinfo.pool(
            pool = context.user_data['poolname'],
            uname = context.user_data['poolUsername'],
            apikey = apiKey
            )
    poolinfo.save()
    logger.info("PoolInfo for user %s is saved.", tgUser.username)
    update.message.reply_text(
            'API Key saved.\n'
            'All done!'
            'Now you can run the /start command.'
            )
    return ConversationHandler.END

def skip_ApiKey(update: Update, context: CallbackContext) -> int:
    """Skips the API Key"""
    tgUser = update.message.from_user
    logger.info("User %s did not set an API Key.", tgUser)
    poolinfo = PoolInfo(tgUser)
    poolinfo.pool(
            pool = context.user_data['poolname'],
            uname = context.user_data['poolUsername']
            )
    poolinfo.save()
    logger.info("PoolInfo for user %s is saved.", tgUser.username)
    update.message.reply_text(
            "API Key is blank.\n"
            "All done!"
            "Now you can run the /start command."
            )
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    tgUser = update.message.from_user
    logger.info("User %s canceled the conversation.", tgUser.username)
    update.message.reply_text(
            'Bye!', reply_markup=ReplyKeyboardRemove()
            )
    return ConversationHandler.END

def show_status(update: Update, context: CallbackContext) -> None:
    """Display the Miner Status."""
    poolinfo = PoolInfo(update.message.from_user.username)
    poolinfo.load()
    msg = ''
    if poolinfo.pools:
        m = []
        for p in poolinfo.pools:
            apiEndPoint = 'https://api.beta.luxor.tech/graphql'
            apiKey = p['apikey']
            pooluser = p['uname']
            try:
                logger.info("Accessing Luxor API for user %s ...", pooluser)
                luxorAPI = API(host = apiEndPoint, method = 'POST', org = 'luxor', key = apiKey)
                wk_details1H = luxorAPI.get_worker_details_1H(pooluser,'BTC',10)
                latest_worker_hashrate = wk_details1H['data']['miners']['edges'][0]['node']['details1H']['hashrate']
                latest_worker_hashrate = float(latest_worker_hashrate)/1000000000000
                prof_act_wk_count = luxorAPI.get_profile_active_worker_count('BTC')
                prof_inact_wk_count = luxorAPI.get_profile_inactive_worker_count('BTC')
                active_wk_count = prof_act_wk_count['data']['getProfileActiveWorkers']
                inactive_wk_count = prof_inact_wk_count['data']['getProfileInactiveWorkers']
                logger.info("Successfully retrieved Luxor API data for user %s.", pooluser)
            except:
                logger.info("Error retrieving data from Luxor API for user %s", pooluser)
                msg = "Error retrieving data from the Pool."

            m.append('Latest Worker Hashrate: ' + "{:.2f}".format(latest_worker_hashrate) + ' TH')
            m.append('Number of Active Workers: ' + active_wk_count)
            m.append('Number of Inactive Workers: ' + inactive_wk_count)
            msg = "\n".join(m).join(['\n', '\n'])
    else:
        msg = "Please set pool information first by using the /start command.\n"

    update.message.reply_text(
        msg
    )

def main() -> None:
    """Run the bot."""
    updater = Updater(config['TELEGRAM']['ApiKey'])
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start',start)],
        states={
            SELECTMININGPOOL: [MessageHandler(Filters.regex('^(Luxor)$'), selectMiningPool)],
            SETPOOLUSERNAME: [MessageHandler(Filters.text,setPoolUsername)],
            SETAPIKEY: [
                CommandHandler('skip', skip_ApiKey),
                MessageHandler(Filters.text,setApiKey),
                ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conv_handler)

    show_status_handler = CommandHandler('status', show_status)
    dispatcher.add_handler(show_status_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()


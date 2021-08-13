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
from poolmonitor import PoolMonitor

config = configparser.ConfigParser()
config.read('.config')

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SELECTMININGPOOL, SETPOOLUSERNAME, SETAPIKEY = range(3)

def start(update: Update, context: CallbackContext) -> int:
    """Starts the bot and asks the user for the Mining Pool."""
    tgUser = update.message.from_user
    logger.info("Starting /start command for User %s", tgUser.username)
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
            'All done!\n'
            'Now you can run the /status command.'
            )
    return ConversationHandler.END

def skip_ApiKey(update: Update, context: CallbackContext) -> int:
    """Skips the API Key"""
    tgUser = update.message.from_user
    logger.info("User %s did not set an API Key.", tgUser.username)
    poolinfo = PoolInfo(tgUser.username)
    poolinfo.pool(
            pool = context.user_data['poolname'],
            uname = context.user_data['poolUsername']
            )
    poolinfo.save()
    logger.info("PoolInfo for user %s is saved.", tgUser.username)
    update.message.reply_text(
            "API Key is blank.\n"
            "All done!\n"
            "Now you can run the /status command."
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
    tgUser = update.message.from_user
    logger.info("Starting /status command for User %s", tgUser.username)
    poolinfo = PoolInfo(update.message.from_user.username)
    poolinfo.load()
    msg = ''
    if poolinfo.pools:
        m = []
        for p in poolinfo.pools:
            apiEndPoint = config['LUXOR']['ApiEndPoint']
            #apiEndPoint = 'https://api.beta.luxor.tech/graphql'
            apiKey = p['apikey']
            pooluser = p['uname']
            poolmonitor = PoolMonitor(p)
            try:
                logger.info("Accessing %s API for user %s ...", p['pool'], pooluser)
                m.append('Latest Worker Hashrate: ' + poolmonitor.getCurrentHashrate('TH'))
                #logger.info('1')
                m.append('Number of Active Workers: ' + poolmonitor.getNumberOfOnlineWorkers())
                #logger.info('2')
                m.append('Number of Inactive Workers: ' + poolmonitor.getNumberOfOfflineWorkers())
                logger.info("Successfully retrieved %s API data for user %s.", p['pool'], pooluser)
                msg = "\n".join(m).join(['\n', '\n'])
            except:
                logger.info("Error retrieving data from Luxor API for user %s", pooluser)
                msg = "Error retrieving data from the Pool."
    else:
        msg = "Please set pool information first by using the /start command.\n"

    update.message.reply_text(
        msg
    )

def checkOnOfflineStatus(context: CallbackContext) -> None:
    """Send the alarm message."""
    job = context.job
    chat_id = job.context['chat_id']
    tgUsername = job.context['tgUsername']
    logger.info("BEGIN: checkOnOfflineStatus() method for user %s", tgUsername)
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
            poolmonitor = PoolMonitor(p)
            try:
                logger.info("Accessing %s API for user %s ...", poolname, pooluser)
                offlineWorkers = int(poolmonitor.getNumberOfOfflineWorkers())
                #logger.info('1')
                prev = poolmonitor.loadNumberOfOfflineWorkers()
                #logger.info('2')
                if prev != -1:
                    if offlineWorkers > 0 and offlineWorkers != prev:
                        if offlineWorkers > 1:
                            plural = 'S'
                        msg += str(offlineWorkers) + " WORKER" + plural + " OFFLINE\n"
                        msg += "Pool: " + poolname + "  Username: " + pooluser + "\n"
                    if offlineWorkers == 0 and offlineWorkers != prev:
                        msg += "All workers are back online."
                    logger.info("Successfully retrieved %s API data for user %s.", poolname, pooluser)
                poolmonitor.saveNumberOfOfflineWorkers(offlineWorkers)
            except:
                logger.info("ERROR: Error in checkOnOfflineStatus() for user %s", tgUsername)
    if msg != '':
        logger.info("checkOnOfflineStatus(): Send message to user.")
        context.bot.send_message(chat_id, text=msg)
    logger.info("END: checkOnOfflineStatus() method for user %s", tgUsername)


def set_OfflineAlert(update: Update, context: CallbackContext) -> None:
    """Activate the On/Offline Alert"""
    tgUser = update.message.from_user
    chat_id = update.message.chat_id
    logger.info("Starting /set command for user %s", tgUser.username)
    try:
        # args[0] should contain the time for hte timer in minutes
        """
        interval = int(context.args[0])
        if interval < 1:
            update.message.reply.text('Number of minutes cannot be less than 1')
            return
        else:
            interval = interval * 60
        """
        interval = 10
        jobname = str(chat_id) + '_offlinealert'
        job_removed = remove_job_if_exists(jobname, context)
        ctxt = {
                'chat_id': str(chat_id),
                'tgUsername': tgUser.username,
                }
        context.job_queue.run_repeating(checkOnOfflineStatus, interval, context=ctxt, name=jobname)

        text = 'Offline Alert activated.'
        if job_removed:
            text += '\n New Interval is set.'
        update.message.reply_text(text)
    except :
        logger.info("set_OfflineAlert(): Error")
        update.message.reply_text('Error setting the Offline Alert. Please contact support.')
            
def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def unset_OfflineAlert(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    jobname = str(chat_id) + '_offlinealert'
    job_removed = remove_job_if_exists(jobname, context)
    text = 'Offline Alert disabled.' if job_removed else 'Offline Alert is not enabled.'
    update.message.reply_text(text)

def main() -> None:
    """Run the bot."""
    updater = Updater(config['TELEGRAM']['ApiKey'])
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start',start)],
        states={
            SELECTMININGPOOL: [MessageHandler(Filters.regex('^(Luxor)$'), selectMiningPool)],
            SETPOOLUSERNAME: [
                CommandHandler('cancel', cancel),
                MessageHandler(Filters.text,setPoolUsername),
                ],
            SETAPIKEY: [
                CommandHandler('cancel', cancel),
                CommandHandler('skip', skip_ApiKey),
                MessageHandler(Filters.text,setApiKey),
                ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conv_handler)

    dispatcher.add_handler(CommandHandler('status', show_status))
    dispatcher.add_handler(CommandHandler("set", set_OfflineAlert))
    dispatcher.add_handler(CommandHandler("unset", unset_OfflineAlert))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()


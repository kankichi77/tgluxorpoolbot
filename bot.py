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
from datetime import datetime

config = configparser.ConfigParser()
config.read('.config')

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SELECTMININGPOOL, SETPOOLUSERNAME, SETAPIKEY = range(3)
OFFLINEALERTQUERY_INTERVAL = 60 * 1

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

def show_status_runonce(update: Update, context: CallbackContext) -> None:
    """Display the Miner Status."""
    tgUser = update.message.from_user
    logger.info("BEGIN: show_status_runonce(): Starting /status command for User %s", tgUser.username)
    #check on/off status first
    checkOnOfflineStatus(
            chat_id = update.message.chat.id,
            tgUsername = update.message.from_user.username,
            init_flag = 0,
            context = context,
            )

    poolmonitor = PoolMonitor(tgUsername = tgUser.username)
    msg = poolmonitor.getStatusMessage()
    update.message.reply_text(
        msg
    )
    logger.info("END: show_status_runonce()")

def checkOnOfflineStatus_scheduled(context: CallbackContext) -> None:
    """Send the alarm message."""
    job = context.job
    chat_id = job.context['chat_id']
    tgUsername = job.context['tgUsername']
    init_flag = int(job.context['init'])
    checkOnOfflineStatus(
            chat_id = chat_id,
            tgUsername = tgUsername,
            init_flag = init_flag,
            context = context,
            )

def checkOnOfflineStatus(
        chat_id,
        tgUsername,
        init_flag,
        context = None,
        ):
    logger.info("BEGIN: checkOnOfflineStatus() for %s", tgUsername)
    poolmonitor = PoolMonitor(tgUsername = tgUsername)
    msg = ''
    msg = poolmonitor.checkOnOfflineStatus(tgUsername, init_flag)
    if msg != '':
        logger.info("checkOnOfflineStatus(): Send message to user.")
        context.bot.send_message(chat_id, text=msg)
    logger.info("END: checkOnOfflineStatus() method for user %s", tgUsername)

def show_status_scheduled(context: CallbackContext) -> None:
    """Display the Miner Status."""
    job = context.job
    chat_id = job.context['chat_id']
    tgUsername = job.context['tgUsername']
    logger.info("BEGIN: show_status_scheduled(): Starting /status_scheduled command for User %s", tgUsername)
    #check on/off status first
    checkOnOfflineStatus(
            chat_id = chat_id,
            tgUsername = tgUsername,
            init_flag = 0,
            )


    poolmonitor = PoolMonitor(tgUsername = tgUsername)
    msg = poolmonitor.getStatusMessage()
    context.bot.send_message(chat_id, text=(msg))
    logger.info("END: show_status_scheduled()")

def set_OfflineAlert(update: Update, context: CallbackContext) -> None:
    """Activate the On/Offline Alert"""
    tgUser = update.message.from_user
    chat_id = update.message.chat_id
    logger.info("Starting /set_offlinealert command for user %s", tgUser.username)
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
        interval = OFFLINEALERTQUERY_INTERVAL 
        jobname = str(chat_id) + '_offlinealert'
        jobname_init = jobname + '_init'
        job_removed = remove_job_if_exists(jobname, context)
        ctxt_init = {
                'chat_id': str(chat_id),
                'tgUsername': tgUser.username,
                'init' : 1
                }
        ctxt = {
                'chat_id': str(chat_id),
                'tgUsername': tgUser.username,
                'init' : 0
                }
        try:
            first_interval = getSecondsUntilNextUpdate()
        except:
            logger.info("getSecondsUntilNextUpdate(): ERROR")
            first_interval = 5
        context.job_queue.run_once(
                checkOnOfflineStatus_scheduled, 
                0, 
                context=ctxt_init, 
                name=jobname_init
                )
        context.job_queue.run_repeating(
                checkOnOfflineStatus_scheduled, 
                interval, 
                first=first_interval, 
                context=ctxt, 
                name=jobname
                )

        text = 'Offline Alert activated.'
        if job_removed:
            text += '\n New Interval is set.'
        update.message.reply_text(text)
    except :
        logger.info("ERROR: set_OfflineAlert()")
        update.message.reply_text('Error setting the Offline Alert.\nPlease contact support.')

def getSecondsUntilNextUpdate():
    return OFFLINEALERTQUERY_INTERVAL 
    now = datetime.now()
    now_min = int(now.strftime('%M'))
    min_to_next = now_min % 5
    if min_to_next > 0:
        min_to_next = 5 - min_to_next
    logger.info("getSecondsUntilNextUpdate(): Now %s", now)
    logger.info("getSecondsUntilNextUpdate(): %s minutes until the next update", min_to_next)
    return min_to_next * 60

def set_AutoMonitor(update: Update, context: CallbackContext) -> None:
    """Activate the On/Offline Alert"""
    tgUser = update.message.from_user
    chat_id = update.message.chat_id
    logger.info("BEGIN: set_AutoMonitor(): Starting /enableAutoMonitor command for user %s", tgUser.username)
    try:
        if not context.args:
            interval = 60
        else:
            interval = int(context.args[0])
        if interval < 1:
            update.message.reply.text('Number of minutes cannot be less than 1')
            return
        else:
            interval = interval * 60
        jobname = str(chat_id) + '_automonitor'
        job_removed = remove_job_if_exists(jobname, context)
        ctxt = {
                'chat_id': str(chat_id),
                'tgUsername': tgUser.username,
                }
        context.job_queue.run_repeating(show_status_scheduled, interval, context=ctxt, name=jobname)

        text = 'Auto Monitor activated.\n'
        if job_removed:
            text += 'New '
        text += f'Interval = {interval/60:g} minutes.'
        update.message.reply_text(text)
    except :
        logger.info("set_AutoMonitor(): Error")
        update.message.reply_text('Error setting the Auto Monitor. Please contact support.')

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

def unset_AutoMonitor(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    jobname = str(chat_id) + '_automonitor'
    job_removed = remove_job_if_exists(jobname, context)
    text = 'Auto Monitor disabled.' if job_removed else 'Auto Monitor is not enabled.'
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


    dispatcher.add_handler(CommandHandler('status', show_status_runonce))
    dispatcher.add_handler(CommandHandler('enableAutoMonitor', set_AutoMonitor))
    dispatcher.add_handler(CommandHandler('disableAutoMonitor', unset_AutoMonitor ))
    dispatcher.add_handler(CommandHandler("enableOfflineAlert", set_OfflineAlert))
    dispatcher.add_handler(CommandHandler("disableOfflineAlert", unset_OfflineAlert))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()


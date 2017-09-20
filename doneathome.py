# -*- coding: utf-8 -*-
import config
import ontime
# https://github.com/eternnoir/pyTelegramBotAPI/#getting-started
import telebot
import time
import sys
import ConfigParser

import logging
import logging.handlers
import signal
import threading
import pickle #  для серилизации
# python /home/dzhukov/My/education/telegramBot/bot/doneathome.py


LOG_FILENAME = "doneathome.log"
CONFIG_PATH = "config.ini"
DEBUG_LEVEL = logging.INFO #('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
LOG_FORMAT = "%(levelname)-8s [%(asctime)s] [%(thread)d : %(funcName)s] %(message)s"


#logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s', level = DEBUG_LEVEL, filename = LOG_FILENAME)

my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)



config = {"telegram_token":"416385445:AAEZI0_oRTg7FC5d4M0fWQqdYBEBvs6UBoI"}

# это множество содержит id активных юзеров
users = set()
LOCK = threading.RLock()
bot = telebot.TeleBot(config['telegram_token'])



def readConfig(path):
    global config

    PConfig = ConfigParser.ConfigParser()
    PConfig.read(path)
    config['telegram_token'] = PConfig.get("telegram","token")
    config['ontime_ontimeUrl'] = PConfig.get("ontime","ontimeUrl")
    config['bot_timePause'] = PConfig.get("bot","timePause")
    config['bot_helpMessage'] = PConfig.get("bot","helpMessage")
    config['bot_commandList'] = PConfig.get("bot","commandList")



@bot.message_handler(commands=['help'])
def botHelp(message):  
    bot.send_message(message.chat.id, config['bot_helpMessage'])
    my_logger.debug(message)


@bot.message_handler(commands=['check'])
def botCheck(message): 
    global users
    global LOCK

    id = int(message.chat.id)
    LOCK.acquire()
    bot.send_message(id, 'count active users = ' + str(len(users)))
    if id in users:
        bot.send_message(id, "вы добавлены, не волнуйся))")
    else:
        bot.send_message(id, "вы не подписаны!")
    LOCK.release() # отпираем замок
    my_logger.debug(str(message) + "users: " + str(users))


@bot.message_handler(commands=['start'])
def botStart(message): 
    global users
    global LOCK

    id = int(message.chat.id)
    LOCK.acquire()
    if id in users:
        bot.send_message(id, "вы уже были добавлены, не нерничай))")
    else:   
        users.add(id)
        bot.send_message(id, "вы добавлены, теперь то не пропустишь))")
    LOCK.release() # отпираем замок
    my_logger.debug(str(message) + "users: " + str(users))


@bot.message_handler(commands=['stop'])
def botStop(message): 
    global users
    global LOCK

    id = int(message.chat.id)
    LOCK.acquire() # накидываем блокировку
    if message.chat.id in users:
        users.remove(id)
        bot.send_message(id, "мониторинг для вас остановлен")
    else:   
        bot.send_message(id, "мы и не запускали))")
    LOCK.release() # отпираем замок
    my_logger.debug(str(message) + "users: " + str(users))


# должен быть в конце, так как является 
# самым общим а проверка на совпадение идет по очереди
@bot.message_handler(content_types=["text"])
def botText(message): 
    bot.send_message(message.chat.id, config['bot_commandList'])
    my_logger.debug(message)






# start/stop worker flag
workerFlag = 1

def worker():
    global workerFlag
    # loop
    while bool(workerFlag):
        doCheck()
        time.sleep(int(config['bot_timePause']))


def doCheck():
    global users
    global LOCK
    global config

    # get time
    timeNow = time.localtime()

    # chech time and send mesage
    if timeNow.tm_hour == 9 or timeNow.tm_hour == 10:
        if ontime.isActionOntime(config):
            #print("SEND!")
            LOCK.acquire() # накидываем блокировку
            for user in users:
                bot.send_message(user,"!!! ВСЕ ПО РУБЛЮ !!!")
            my_logger.debug("!!! ВСЕ ПО РУБЛЮ !!!" + " send to " + str(user))
            LOCK.release() # отпираем замок
        else:
            pass
            # for user in users:
            #     bot.send_message(user,'проверка (учти промежуток опроса)')
             


# TODO надо чтоб сохраняло читало и 
def readSaveUsers(commandType):
    global users

    if commandType == 'save':
        print('save users')
        with open('users.txt', 'wb') as f:
            pickle.dump(users, f) 
    
    if commandType == 'load':
        print('load users')
        try:
            with open('users.txt', 'rb') as f:
                users = pickle.load(f)
        except IOError as e:
            my_logger.info('file [users.txt] not found')
            my_logger.info('file [users.txt] was create')
            with open('users.txt', 'wb') as f:
                pickle.dump(users, f)



# start/stop bot flag
botFlag = 1

def mySIGINT(arg1, arg2):
    global workerFlag

    print('Завершение, необходимо подождать ' + str(config['bot_timePause']) + ' секунд')
    readSaveUsers('save')
    my_logger.info('save users')
    workerFlag = 0
    botFlag = 0
    
    my_logger.info('interupt programm by [ ctrl + c ]')
    sys.exit(0)




def main():
    global users
    global workerFlag
    global botFlag
    global bot


    # loger rotate config
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=9000000, backupCount=5)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    my_logger.addHandler(handler)

    # read config file [config.ini]
    readConfig(CONFIG_PATH)
    my_logger.debug('read config ' + CONFIG_PATH)

    # read [users.txt]
    readSaveUsers('load')
    my_logger.debug('read users')

    thread_ = threading.Thread(target=worker)
    print('start worker')
    my_logger.info('start worker')
    thread_.start()

    # reaction for [ ctrl+c - SIGINT - 2 ]
    signal.signal(2,mySIGINT)


    print('start bot')
    my_logger.info('start bot')
    while botFlag:

        try:
            bot.polling(none_stop=True) # это запуск бота

        except Exception as e:
            # write [users.txt]
            # readSaveUsers('save')
            time.sleep(15) 
            my_logger.info('restart bot' + e)




if __name__ == '__main__':
     main()
     # bot.polling(none_stop=True) # это запуск бота
     
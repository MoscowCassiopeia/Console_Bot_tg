import os
import subprocess
import logging
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import RegexHandler
import config as cfg

'''
Бот для телеграма, который позволяет использовать телеграм как консоль вашего компьютера.
Выполнит любую команду которая отдает свои данны через stdout.
Некоторые команды реализованы в этом скрипте:
- "cd dir" смена директории
- "cd .." подняться в родительскую директорию
- "get file" получить указанный файл 
Использование:
- вписать нужные параметры в блоке "Настройки"
- запустить файл скрипта
- для включения контекста управления, набрать в чате с ботом /dir
  в ответ получите информационное сообщение о том что доступ разрешен и контекст включен
- отправьте нужную команду, примеры команд: "ls", "pwd", "ls -al", "cd ..", "cd dir"
- выход из контекста "dir_exit"
'''


#Для хранения chat_id у которых включен контекст
context = []

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

updater = Updater(token=cfg.TOKEN_BOT)
dispatcher = updater.dispatcher

def access_denied(update):
    '''Шлёт сообщение о запрете доступа'''
    update.message.reply_text('Access Denied')    

def send_file(bot, update, file):
    '''
    Шлет в телеграм указанный файл (file)
    '''
    bot.send_document(chat_id=update.message.chat_id,
                      document=open(file, 'rb'))

def check_access(update):
    '''
    Проверяет, включен ли контекст у chat_id
    '''
    if update.message.chat_id in cfg.ACCESS_CHAT_ID:
        return True
    else:
        return False

def enable_context(update):
    '''
    Помещает чат id в список тех, у кого включен контекст
    '''
    global context
    context.append(update.message.chat_id)

def disable_context(update):
    '''
    Выключает контекст.
    (Удаляет чат id из списка тех, у кого включен контекст)
    '''
    global context
    context.remove(update.message.chat_id)

def is_context(update):
    '''
    Проверка, включен ли у пользователя контекст
    '''
    if update.message.chat_id in context:
        return True
    else:
        return False

def split_message(txt):
    '''
    Если сообщение больше 4096 символов utc-8, разделяет его
    на несколько, не превышающих 4096, возвращает лист разделенных сообщений.
    '''
    msgs = []     
    if len(txt) > 4096:
        tmp_msg = ''        
        txt = txt.split('\n')        
        for line in txt:
            if len(tmp_msg) + len(line) + 1 > 4096:
                msgs.append(tmp_msg)
                tmp_msg = ''            
            tmp_msg += f'{line}\n'
        else:
          msgs.append(tmp_msg)
        return msgs
    else:
        return [txt]
    
                
def off_cntx(bot, update):
    '''
    Выключает контекст
    '''
    if not is_context(update):
        update.message.reply_text('Already exit')
    else:
        disable_context(update)
        update.message.reply_text('Context Disable')
        logging.info(f'{update.message.chat_id}:{update.message.text}')

def cmd(bot, update):
    '''
    Принимает команды утилит, внутри контекста и передает их на выполнение
    '''
    if not is_context(update):
        return None
    else:
        args = update.message.text.split(' ')        
        logging.info(f'args = {args}')
        try:
            list_out = subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            std_out = str(list_out.stdout.read(), 'utf-8')
            for msg in split_message(std_out):
                update.message.reply_text(f'`{msg}`', parse_mode='markdown')
            logging.info(f'{update.message.chat_id}:{update.message.text}')
        except Exception as err:
            update.message.reply_text(f'`{err}`', parse_mode='markdown')
            logging.error(f'{update.message.chat_id}:{update.message.text}:{err}')
        

def cmd_cd(bot, update):
    '''
    Меняет текущую директорию
    '''
    if not is_context(update):
        return None
    else:
        commd, name_dir = update.message.text.split(' ', maxsplit=1)
        if os.path.isdir(name_dir):
            os.chdir(name_dir)
            logging.info(f'{update.message.chat_id}:{commd} {name_dir}')
        else:
            update.message.reply_text('Bad argument cd [this]')       
            logging.error(f'{update.message.chat_id}:{commd} {name_dir}') 

def cmd_up(bot, update):
    '''
    Меняет текущую директорию на уровень выше (cd ..)
    '''
    if not is_context(update):
        return None
    else:
        os.chdir('..')
        logging.info(f'{update.message.chat_id}:{update.message.text}')

def cmd_get(bot, update):
    '''
    Высылает требуемый файл
    '''    
    if not is_context(update):
        return None
    else:
        cmd, name_object = update.message.text.split(' ', maxsplit=1)
        if os.path.isfile(name_object):
            send_file(bot, update, name_object)
            logging.info(f'{update.message.chat_id}:{cmd} {name_object}')
        else:
            update.message.reply_text('Bad argument get [this]')
            logging.error(f'{update.message.chat_id}:{cmd} {name_object}: Bad Argumetnt')

def on_cntx(bot, update):
    '''
    Включение контекста
    '''
    logging.info(f'bot_var = {bot}')
    if check_access(update) == False:
        access_denied(update)
        logging.warning(f'Access Denied: {update.message.chat_id}')
        return None
    elif not is_context(update):
        enable_context(update)
        update.message.reply_text('Access Granted, Context Enabled')
        logging.info(f'Granted Access:Enable Context:{update.message.chat_id}')
    else:
        update.message.reply_text('Context Already Enabled')    
        

def main():
    cd_up_handler = RegexHandler(pattern=r'^cd \.\.$', callback=cmd_up)
    cd_handler = RegexHandler(pattern=r'^cd .{1,256}$', callback=cmd_cd)    
    cmd_handler = RegexHandler(pattern=r'^.{1,1024}$', callback=cmd)
    context_handler = CommandHandler(cfg.ON_CONTEXT_CMD, on_cntx, pass_user_data=False)
    exit_context_handler = CommandHandler(cfg.OFF_CONTEXT_CMD, off_cntx)
    get_handler = RegexHandler(pattern='^get .{1,256}$', callback=cmd_get)    
   
    dispatcher.add_handler(cd_up_handler)
    dispatcher.add_handler(get_handler)
    dispatcher.add_handler(cd_handler)
    dispatcher.add_handler(context_handler)
    dispatcher.add_handler(exit_context_handler)
    dispatcher.add_handler(cmd_handler)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Origine da: Simple Bot to reply to Telegram messages
"""
MIT License

Copyright (c) 2016 dave4th

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

=============================================================================

This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.

-= MyChange =-
Questo bot ad ora: Tue 13 Dec 2016 08:28:20 AM CET
Visualizza help
Elenca i files .CSV generati ed utilizzati per i grafici dalla centralina "level 1"
Genera un'immagine in PNG di questi CSV e la invia all'utente su richiesta.

"""

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging

# 
import glob
import telegram    # Serve per il "ParseMode"
import pygal
import pandas
import os
import mjl, flt    # mhl, non serve e neanche l'ho copiata nella directory
import redis
import subprocess


# Parametri generali
# 
DirBase="/var/www"    # la directory root del webserver
ConfigFile=DirBase+"/conf/config.json"    # il file della configurazione redis


# Il mio id per i/comandi e le chat private, che ancora non uso e non so se sia e come sia "possibile".
mychatid='79111109'

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    update.message.reply_text('''
* Questo bot *
Elenca i files ".csv" presenti nella 'root' "/var/www/" della centralina livello 1.
Genera, se richiesto, l'immagine PNG, che viene inviata in chat.
Visualizza i valori delle chiavi redis.
Visualizza i daemons (running/not running)
Ha ancora l'eco attivo, quindi rimanda i messaggi ricevuti :P

I comandi utili sono:
/start - Questo messaggio
/help - Elenco dei comandi disponibili
/listacsv - Elenco dei files CSV
/image <nomefile.csv> - Genera ed invia l'immagine del grafico (puo` impiegare diversi minuti, dipende dalla quantita` dei dati)
/keys <filtro> - Visualizza le chiavi selezionate ed il loro contenuto
/keysfilters - Esempi di filtro/selezione chiavi (utili per il copia/incolla)
/daemons - Visualizzazione dei daemons (my debug)

Fri 16 Dec 2016 09:03:46 AM CET
E` ora possibile visualizzare il valore di una chiave digitando la rispettiva chiave dei valori senza nessun'altro comando, per esempio:
\t\tI:Mobile:Mobile:Mobile:Temperatura:ST1:Valori
Oppure, puoi selezionare di visualizzare:
- Temperatura
- Umidita
- Pioggia
Digitando le parole cosi` come scritte
    ''')
    keyboard = [
                 [telegram.KeyboardButton('/help')],
                 [telegram.KeyboardButton('Temperatura')],
                 [telegram.KeyboardButton('Umidita')],
                 [telegram.KeyboardButton('Pioggia')],
               ]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.sendMessage(update.message.chat_id, text="I'll be back ..", reply_markup=reply_markup)


def help(update, context):
    context.bot.sendMessage(update.message.chat_id, text='<b>Help / Aiuto</b>', parse_mode=telegram.ParseMode.HTML)
    context.bot.sendMessage(update.message.chat_id, text='''
/listacsv : Elenco dei files CSV
/image <nomefile.csv> : Genera ed invia il grafico in formato PNG (Attenzione: puo` impiegare diversi minuti)
/keys <keys-filter> : Visualizzazione delle chiavi redis
/keysfilters : Esempi di filtri per le chiavi redis
/daemons : Daemons (debug)
/testid : Visualizza ID CHAT (my debug)
''')
    keyboard = [
                 [telegram.KeyboardButton('/help')],
                 [telegram.KeyboardButton('Temperatura')],
                 [telegram.KeyboardButton('Umidita')],
                 [telegram.KeyboardButton('Pioggia')],
               ]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.sendMessage(update.message.chat_id, text="I'll be back ..", reply_markup=reply_markup)


def listacsv(update, context):
    Dirs = ["/var/www/", "/var/www/archive/"]
    # Cerco i CSV
    # Prima quelli della "archive", poi aggiungo in testa quella della www
    #FileList = sorted(glob.glob(Dirs[1]+"*.csv"))
    #FileList[0:0] = sorted(glob.glob(Dirs[0]+"*.csv"))
    # Uso solo quelli della "root"
    FileList = sorted(glob.glob(Dirs[0]+"*.csv"))
    context.bot.sendMessage(update.message.chat_id, text='<b>Elenco files:</b>', parse_mode=telegram.ParseMode.HTML)
    keyboard = [[telegram.KeyboardButton('/help')]]    # preparo la tastiera, e` una lista python
    for i in range(len(FileList)):
        context.bot.sendMessage(update.message.chat_id, text='/image '+FileList[i])
        testo='/image '+FileList[i]
        keyboard.append([telegram.KeyboardButton(testo)])    # Ho messo le quadre perche` i testi sono lunghi ed e` meglio incolonnare i pulsanti
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.sendMessage(update.message.chat_id, text="I'll be back ..", reply_markup=reply_markup)


def image(update, context):
    try:
        if os.path.exists(context.args[0]):
            context.bot.sendMessage(update.message.chat_id, text='<b>Attenzione, questa operazione puo` richiedere diversi minuti !</b>', parse_mode=telegram.ParseMode.HTML)
            csvi = pandas.read_csv(context.args[0])
            # Tipo di chart "Line"
            line_chart = pygal.Line(x_label_rotation=30,x_labels_major_every=100, show_minor_x_labels=False)
            # Lista colonne, colonne contiene il nome delle colonne dal csv (la prima riga)
            # a noi servira` piu` per sapere quante ce ne sono, che il nome
            colonne=csvi.columns.tolist()
            # Genero il titolo del grafico prendendo i nomi delle colonne
            titlegraph = colonne[1]    # Scarto la prima che e` sempre data e ora
            # .. quindi tutte le altre, se ne esistono piu` di due
            if len(colonne) >= 2:
                for i in range(2,len(colonne)):
                    titlegraph = titlegraph+","+colonne[i]
            # Titolo della chart
            line_chart.title=titlegraph
            # Creo una lista vuota, che conterra` altre liste
            colonna = []
            # Inizializzo le varibili di lista
            for i in range(len(colonne)):
                update.message.reply_text('Scansione colonna '+str(i)+' ..')
                # Devo trasformare tutti i dati (nelle colonne) in liste, per darli in pasto a pygal
                # Per ogni riga ... (index = numero di riga, row = valore)
                colonnatemp = []    # Preparo la lista vuota
                for index, row in csvi.iterrows():
                    if (row[colonne[i]] == "err"):
                        colonnatemp.append(None)    # Non chiedetemi perche` funziona, non lo so neanche io.
                    else:
                        colonnatemp.append(row[colonne[i]])
                colonna[i:i] = [colonnatemp]    # Metto la lista nella posizione della colonna
            update.message.reply_text('Generazione grafico ..')
            # Sulla x ci vanno le date, e` sempre la prima colonna
            line_chart.x_labels=colonna[0]
            # Il resto delle colonne, dalla 1 alla fine, sono liste della chart da mettere in grafico
            for i in range(1,len(colonne)):
                # Serve il nome della colonna, che prendo dalla variabile colonne, poi la lista dei valori
                line_chart.add(colonne[i],colonna[i])
            update.message.reply_text('Inizio rendering ..')
            # Render
            line_chart.render_to_png('image.png')
            context.bot.sendPhoto(update.message.chat_id, photo=open('image.png', 'rb'))
        else:
            context.bot.sendMessage(update.message.chat_id, text='Devi specificare il nome di un file ".csv" esistente.')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /image <nomefile.csv>')


def keys(update, context):
    try:
        # Apro il database Redis con l'istruzione della mia libreria
        MyDB = flt.OpenDBFile(ConfigFile)
        # Per ogni campo ... stampo il campo ed il suo valore. (la funzione "Decode()" serve per trasformare "bin->str")
        # Creo le opportune variabili per le selezioni/modifiche delle forms seguenti
        RedisKeyString=[]
        RedisKeyHash=[]
        RedisKeyList=[]
        RedisKeySet=[]
        for i in MyDB.keys(context.args[0]):
            #print (flt.Decode(i))
            # Ho dovudo decodificare due volte per leggere la stringa del tipo di chiave e controllarne l'uguaglianza
            if flt.Decode(MyDB.type(flt.Decode(i))) == "hash":
                #print (MyDB.type(flt.Decode(i)),": ",MyDB.hgetall(flt.Decode(i)))
                """ Composizione del testo da visualizzare:
                    nella prima riga il nome della chiave in grossetto (c'e` il ritorno a capo \n)
                    dalla seconda riga i valori/contenuto della chiave
                """
                testo="<b>"+str(flt.Decode(i))+"\n</b>"+str(MyDB.type(flt.Decode(i)))+": "+str(MyDB.hgetall(flt.Decode(i)))
                context.bot.sendMessage(update.message.chat_id, text=testo, parse_mode=telegram.ParseMode.HTML)
                RedisKeyHash.append(flt.Decode(i))
            elif flt.Decode(MyDB.type(flt.Decode(i))) == "string":
                #print (MyDB.type(flt.Decode(i)),": ",MyDB.get(flt.Decode(i)))
                testo="<b>"+str(flt.Decode(i))+"\n</b>"+str(MyDB.type(flt.Decode(i)))+": "+str(MyDB.get(flt.Decode(i)))
                context.bot.sendMessage(update.message.chat_id, text=testo, parse_mode=telegram.ParseMode.HTML)
                RedisKeyString.append(flt.Decode(i))
            elif flt.Decode(MyDB.type(flt.Decode(i))) == "list":
                #print (MyDB.type(flt.Decode(i)),": ",MyDB.llen(flt.Decode(i)),"valori, l'ultimo e`: ",MyDB.lindex(flt.Decode(i),"-1"))
                testo="<b>"+str(flt.Decode(i))+"\n</b>"+str(MyDB.type(flt.Decode(i)))+": "+str(MyDB.llen(flt.Decode(i)))+"valori, l'ultimo e`: "+str(MyDB.lindex(flt.Decode(i),"-1"))
                context.bot.sendMessage(update.message.chat_id, text=testo, parse_mode=telegram.ParseMode.HTML)
                RedisKeyList.append(flt.Decode(i))
            elif flt.Decode(MyDB.type(flt.Decode(i))) == "set":
                #print (MyDB.type(flt.Decode(i)),": ",MyDB.smembers(flt.Decode(i)))
                testo="<b>"+str(flt.Decode(i))+"\n</b>"+str(MyDB.type(flt.Decode(i)))+": "+str(MyDB.smembers(flt.Decode(i)))
                context.bot.sendMessage(update.message.chat_id, text=testo, parse_mode=telegram.ParseMode.HTML)
                RedisKeySet.append(flt.Decode(i))
            else:
                print (MyDB.type(flt.Decode(i)),": ","Non ancora contemplata")
        # Fine visualizzazione
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /keys <keys-filter>')



def keysfilters(update, context):
    context.bot.sendMessage(update.message.chat_id, text='/keys * (tutte le chiavi)')
    context.bot.sendMessage(update.message.chat_id, text='/keys *Temperatura*')
    context.bot.sendMessage(update.message.chat_id, text='/keys *I:Casa:PianoUno:*')
    context.bot.sendMessage(update.message.chat_id, text='/keys *Valori*')
    context.bot.sendMessage(update.message.chat_id, text='/keys *graph*')
    context.bot.sendMessage(update.message.chat_id, text='/keys *alarm*')
    keyboard = [
                 [telegram.KeyboardButton('/help')],
                 [telegram.KeyboardButton('/keys *')],
                 [telegram.KeyboardButton('/keys *Temperatura*:Valori')],
                 [telegram.KeyboardButton('/keys *Umidita*:Valori')],
                 [telegram.KeyboardButton('/keys *Pioggia*:Valori')],
                 [telegram.KeyboardButton('/keys *Valori')]
               ]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.sendMessage(update.message.chat_id, text="I'll be back ..", reply_markup=reply_markup)

def daemons(update, context):
    #print (flt.Decode(subprocess.check_output(['/var/www/cgi-bin/mqtt2redis_init.d.sh','status'])))
    testo=flt.Decode(subprocess.check_output(['/var/www/cgi-bin/mqtt2redis_init.d.sh','status']))
    context.bot.sendMessage(update.message.chat_id, text=testo)
    # Gruppi Redis
    # Non riesco a filtrare con una normale 'regex', mi son stufato e allora prendo tutti
    # quelli che hanno "sets:*:Config" e poi eliminero` il finale ":Config"
    MyDB = flt.OpenDBFile(ConfigFile)
    SetsRedis = flt.DecodeList(MyDB.keys("sets:*:Config"))
    # Eliminazione finale ..
    for i in range (len(SetsRedis)):
        # La lista e` (uguale alla lista puntata da i [i]),
        # presa per tutta la sua lunghezza di caratteri [:L-7],
        # tolto 7, che e` la lunghezza di ":Config"
        SetsRedis[i] = SetsRedis[i][:len(SetsRedis[i])-7]
    for i in range (len(SetsRedis)):
        testo=flt.Decode(subprocess.check_output(['/var/www/cgi-bin/setsgraph_init.d.sh','status',SetsRedis[i]]))
        # Genero una stringa solo per avere un'output decente, e perche` lo 'status', non riporta il parametro del demone
        context.bot.sendMessage(update.message.chat_id, text='<b>'+SetsRedis[i]+'</b>\n'+testo, parse_mode=telegram.ParseMode.HTML)
        testo=flt.Decode(subprocess.check_output(['/var/www/cgi-bin/setsalarms_init.d.sh','status',SetsRedis[i]]))
        # Genero una stringa solo per avere un'output decente, e perche` lo 'status', non riporta il parametro del demone
        context.bot.sendMessage(update.message.chat_id, text='<b>'+SetsRedis[i]+'</b>\n'+testo, parse_mode=telegram.ParseMode.HTML)


def testid(update, context):
    context.bot.sendMessage(update.message.chat_id, text='Chat ID: <b>'+str(update.message.chat_id)+'</b>', parse_mode=telegram.ParseMode.HTML)


# Ho lasciato la funzione echo, modificandola un po` ;)
def echo(update, context):
    if update.message.text == 'davide':
        update.message.reply_text('Ideatore del bot: http://github.com/dave4th')
    elif update.message.text == 'mirco':
        update.message.reply_text('Beta tester: http://github.com/bergam')
    #elif update.message.text == 'credits':
    #    update.message.reply_text('davide, mirco, raspibo')
    elif update.message.text == 'raspibo':
        update.message.reply_text('http://github.com/raspibo\nhttp://www.raspibo.org')
    elif update.message.text == 'bot':
        update.message.reply_text('http://github.com/raspibo/bot4livello1')
    elif (update.message.text == 'livello1') or (update.message.text == 'level1') or (update.message.text == 'centralina'):
        update.message.reply_text('http://www.raspibo.org/wiki/index.php/Centralina_livello_1')
    #elif update.message.text.split(":")[0] == 'I':    # Per ora solo le "I" (input), ma domani ci saranno anche le "O" (output) ?
    #    try:
    #        if update.message.text.split(":")[6] == 'Valori':
    #            # Apro il database Redis con l'istruzione della mia libreria
    #            MyDB = flt.OpenDBFile(ConfigFile)
    #            # Elimino "Valori" dalla srtringa con l'operazione [:-7] che toglie sette lettere dalla fine (anche il :)
    #            Descrizione=flt.Decode(MyDB.hget(update.message.text[:-7],"Descrizione"))
    #            # Prendo l'ultimo ":Valori" dalla chiave (nella chiave, e` un gruppo "sets")
    #            # Il valore e` dopo la virgola 		.split(",")[1]
    #            # perche` prima c'e` la data		.split(",")[0]
    #            Data=flt.Decode(MyDB.lindex(update.message.text,-1)).split(",")[0]
    #            Valore=flt.Decode(MyDB.lindex(update.message.text,-1)).split(",")[1]
    #            update.message.reply_text(Descrizione+": "+Valore+" ["+Data+"]")
    #    # except non e` ancora stato verificato
    #    except (IndexError, ValueError):
    #        update.message.reply_text('Qualcosa e` andato storto')
    #        update.message.reply_text('La chiave specificata non contiene valori ?')
    elif (update.message.text == 'Temperatura') or (update.message.text == 'Umidita') or (update.message.text == 'Pioggia') or (update.message.text.split(":")[0] == 'I'):
        # Apro il database Redis con l'istruzione della mia libreria
        MyDB = flt.OpenDBFile(ConfigFile)
        for i in MyDB.keys('*'+update.message.text+'*'):
            if flt.Decode(MyDB.type(flt.Decode(i))) == "list":
                try:
                    if flt.Decode(i).split(":")[6] == 'Valori':
                        # Elimino "Valori" dalla srtringa con l'operazione [:-7] che toglie sette lettere dalla fine (anche il :)
                        """ Non riesco ad evitare l'errore quando la descrizione contiene "`", come per esempio: "Umidita`"
                            Il programma funziona ugualmente, anche se compare l'errore.
                        """
                        if MyDB.hexists(flt.Decode(i)[:-7],"Descrizione"):    # Se esiste ..
                            #Descrizione=flt.Decode(MyDB.hget(flt.Decode(i)[:-7],"Descrizione"))
                            Descrizione=str(MyDB.hget(flt.Decode(i)[:-7],"Descrizione"), 'utf-8')       # Funziona ugualmente come il decode !
                        else:
                            Descrizione="Senza descrizione"
                        # Prendo l'ultimo ":Valori" dalla chiave (nella chiave, e` un gruppo "sets")
                        # Il valore e` dopo la virgola 		.split(",")[1]
                        # perche` prima c'e` la data		.split(",")[0]
                        Data=flt.Decode(MyDB.lindex(flt.Decode(i),-1)).split(",")[0]
                        Valore=flt.Decode(MyDB.lindex(flt.Decode(i),-1)).split(",")[1]
                        """ Usati per verifiche decodifica errore su parole con accento inverso (Umidita`)
                        """
                        #print(MyDB.hget(flt.Decode(i)[:-7],"Descrizione"))
                        #print(type(MyDB.hget(flt.Decode(i)[:-7],"Descrizione")))
                        #print(Descrizione)
                        #print(type(Descrizione))
                        update.message.reply_text(Descrizione+": "+Valore+" ["+Data+"]")
                except (IndexError, ValueError):
                    update.message.reply_text('Qualcosa e` andato storto')
                    update.message.reply_text('La chiave specificata non contiene valori ?')
            #else:
            #    update.message.reply_text('Non ho trovato niente da visualizzare')
    else:
        update.message.reply_text(update.message.text)
        #update.message.reply_text('(e` attiva la funzione "echo" dei messaggi \'inutili\')')


def error(update, context):
    logger.warning('Update "%s" caused error "%s"' % (update, context.error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("YOUR TOKEN", use_context=True)
    
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("listacsv", listacsv))
    dp.add_handler(CommandHandler("image", image, pass_args=True))
    dp.add_handler(CommandHandler("keys", keys, pass_args=True))
    dp.add_handler(CommandHandler("testid", testid))
    dp.add_handler(CommandHandler("keysfilters", keysfilters))
    dp.add_handler(CommandHandler("daemons", daemons))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

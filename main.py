import sys
import json
from time import sleep
from irc import WooferBotFactory
import handler
import api
import tweepy
import auto
from twisted.internet import reactor, threads
from twisted.python.rebuild import rebuild
from settings import config

# global variables
bots = []

def keyboard_handler():
    print 'Hi, keyboard input here plz'
    while True:
        cmd = raw_input()
        if cmd == 'q': break
        elif cmd == ' ':
            command = raw_input("What do you want to do?:")
            if command.lower() == "join":
                newChannel = raw_input("Which channel do you want to join?:")

                if newChannel in config['channels']:
                    print 'We\'re already in channel #{}'.format(newChannel)
                else:
                    # add to last bot, or create new bot if none exist yet
                    if len(bots) > 0:
                        (bot, tcp) = bots[-1]
                    else:
                        bot = WooferBotFactory([newChannel])
                        tcp = reactor.connectTCP("irc.twitch.tv", 6667, bot)
                        bots.append((bot, tcp))
                    bot.addChannel(newChannel)

            elif command.lower() == "chat":
                channel = raw_input("Where do you want to chat?:")
                # find bot associated to channel
                try:
                    bot = next(bot for (bot,tcp) in bots if channel in bot.channels)
                    msg = raw_input("What do you want to say?:")
                    bot.irc.say(channel, msg)
                except StopIteration:
                    print 'I don\'t know that channel'

            elif command.lower() == "reload":
                rebuild(handler)
                rebuild(api)

    print 'done'

def create_bots():
    global config
    # create bots, 10 channels per instance
    split_by_n = lambda A, n: [A[i:i+n] for i in range(0, len(A), n)]
    for x in split_by_n(config['channels'], n=10):
        # create factory protocol and application
        bot = WooferBotFactory(x)
        tcp = reactor.connectTCP("irc.twitch.tv", 6667, bot)
        bots.append((bot, tcp))
        # throttle so twitch accepts us
        sleep(5)

def shutdown():
    # stop handler, close sockets
    handler.WooferHandler.stop()
    for (bot, tcp) in bots:
        bot.irc.quit()
        tcp.disconnect()
    reactor.stop()


if __name__ == '__main__':

    # register the thread func that handles all dispatched commands
    handler.WooferHandler.start()

    # register keyboard handler, when it's down call shutdown()
    threads.callMultipleInThread([(keyboard_handler, [], {}), (shutdown, [], {})])

    # open sockets once we start the message loop
    reactor.callInThread(create_bots)

    # run bots
    reactor.run()
    
    # save settings
    config.save()

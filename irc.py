#!/usr/bin/env python
# coding: utf-8
import time
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from logger import ConsoleLogger
from settings import config
from handler import WooferHandler
from twisted.python.rebuild import Sensitive


class WooferBot(irc.IRCClient):

    def __init__(self):
        self.logger = ConsoleLogger()
        self.nickname = config['nickname']
        self.password = config['password']
        self.lineRate = 1.0

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger.log("[connected at %s]" % time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" % time.asctime(time.localtime(time.time())))

    # callbacks for events
    def signedOn(self):
        """Called when bot has successfully signed on to server."""
        for c in self.factory.channels:
            self.join(c)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))
        WooferHandler.handleMessage(self, user, channel.replace('#', ''), msg)

        # simple commands can be handled here locally, but ones that
        # require external lookups should be scheduled on the dispatcher

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))

    # irc callbacks
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return self.nickname + '^'


class WooferBotFactory(protocol.ClientFactory):
    def __init__(self, channels):
        self.channels = channels
        self.irc = None

    def buildProtocol(self, addr):
        self.irc = WooferBot()
        self.irc.factory = self
        return self.irc

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason

    def addChannel(self, channel):
        if channel not in config['channels']:
            self.channels.append(channel)
            if not self.irc is None:
                self.irc.join(channel)
            if channel in config['users'].keys():
                config['users'][channel]['status'] = 'user'
            else: 
                config['users'][channel] = {}
                config['users'][channel]['status'] = 'user'
            config['channels'].append(channel)
            config.sanitize() # ensures config is valid
            config.save()
        else:
            print 'channel was already in config'

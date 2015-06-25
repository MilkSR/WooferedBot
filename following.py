import time
import json
import urllib
from threading import Semaphore
from twisted.python.rebuild import Sensitive, rebuild
from settings import config

class WooferBotFollowHandler(Sensitive):
    def __init__(self):
        self.die = False
        self.semaphore = Semaphore(0)

    def getFollowing(self, user):
        return config['following'][user].keys()

    def getLive(self, user, bot2):
        list = getFollowing(user)
        for follow in list:
            liveUrl = "https://api.twitch.tv/kraken/streams/" + follow
            liveResponse = urllib.urlopen(liveUrl);
            liveData = json.load(liveUrl)
            if liveData['stream'] is not None:
                if config['following'][user] == 'offline': bot2.say(user, "{} just went live go watch him at twitch.tv/{}".format(follow))
                config['following'][user] = 'live'
            elif liveData['stream'] is None: config['following'][user] = 'offline'
            return
                

    def sendLive(self):
        if int(time.strftime("%M")) % 2 == 0:   
            for user in config['following'].keys():
                getLive(user)
            return
            
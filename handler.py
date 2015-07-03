import time
import re
import json
import random
import datetime
import urllib
import sys
import math
import BeautifulSoup
from collections import deque
from threading import Semaphore
from twisted.internet import reactor
from twisted.python.rebuild import Sensitive, rebuild
from settings import config

YOUTUBE_LINK = re.compile(r"""\b(?:https?://)?(?:m\.|www\.)?youtu(?:be\.com|\.be)/(?:v/|watch/|.*?(?:embed|watch).*?v=)?([a-zA-Z0-9\-_]+)""")


#--------------TODO--------------
#Random SRL Host
#Chat logging - WIP
#Clean up speedrun garbage
#Mod logging
#?Email thing?

class WooferBotCommandHandler(Sensitive):
    def __init__(self):
        self.die = False
        self.semaphore = Semaphore(0)
        self.commandQueue = deque()

    def handleMessage(self, bot, user, channel, message):
            self.handleYoutube(bot, user, channel, message)
            if user not in config['users'][channel]['ignore'] and user not in config['globalignorelist']:
                self.updateDogs(bot, channel, message)
                self.updateCustom(bot, channel, message)
                for (prefix, handler, dispatch) in self.commands:
                    if message.lower().startswith(prefix):
                        if dispatch: # handle in separate thread
                            args = (handler, bot, user, channel, message)
                            self.commandQueue.append(args)
                            self.semaphore.release()
                        else:
                            try:
                                getattr(self, handler)(bot, user, channel, message)
                            except Exception,e:
                                print 'Error while handling command: ' + e.message
                                print sys.exc_traceback.tb_lineno 
                                print e

    def updateDogs(self, bot, channel, message):
        for dog in config['dogs']:
            if dog in message and config['users'][channel]['dogs']:
                config['dogsc']['dogCount'][channel][dog] += 1
                if config['dogsc']['dogCount'][channel][dog] == 3:
                    # say dog name in channel
                    bot.say(channel, dog)
                    config['dogsc']['dogCount'][channel][dog] = 0

    def updateCustom(self, bot, channel, message):
        for command in config['users'][channel]['custom']['commands'].keys():
            if message.startswith(command): bot.say(channel, config['users'][channel]['custom']['commands'][command])
        for emote in config['users'][channel]['custom']['emotes'].keys():
            if emote in message:
                config['users'][channel]['custom']['emotes'][emote] += 1
                if config['users'][channel]['custom']['emotes'][emote]  == 3:
                    bot.say(channel, emote)
                    config['users'][channel]['custom']['emotes'][emote] = 0
        return

    # def updateLog(self, bot, channel, message):
        # if channel not in config['logging']: return
        # [channel]['log'].append(time.strftime("[%H:%M:%S]") + ' <' + user + '> ' + message)
        
    def handleYoutube(self, bot, user, channel, message):
        if not config['users'][channel]['youtube']: return
        match = YOUTUBE_LINK.search(message)
        if not match:
            return

        self.commandQueue.append(('executeYoutube', bot, user, channel, match.group(1)))
        self.semaphore.release()
            
    def executeJoin(self, bot, user, channel, message):
        parts = message.split(' ')
        # this command can be used in two ways:
        # 1) any user can enter +join in any of the bot admin channels,
        #    causing the bot to join the user's channel
        # 2) admins can request the bot to join anybodies channel
        #    entering +join <user>
        if len(parts) == 1 and config['users'][channel]['admin']:
            joinChannel = user
        elif len(parts) == 2 and config['users'][user]['admin']:
            joinChannel = parts[1]
        else:
            return # invalid syntax

        if joinChannel in config['users'].keys():
            bot.say(channel, '{} is already in channel #{}!'.format(config['nickname'], joinChannel))
        else:
            bot.say(channel, '{} will join #{} shortly.'.format(config['nickname'], joinChannel))
            config['users'][joinChannel]['admin'] = False
            config['users'][joinChannel]['dogs'] = True
            config['users'][joinChannel]['dogfacts'] = False
            config['users'][joinChannel]['kadgar'] = False
            config['users'][joinChannel]['speedrun'] = False
            config['users'][joinChannel]['youtube'] = False
            config['users'][joinChannel]['custom'] = {}
            config['users'][joinChannel]['custom']['commands'] = {}
            config['users'][joinChannel]['custom']['emotes'] = {}
            config['users'][joinChannel]['ignore'] = []
            config['channels'].append(joinChannel)
            config.save()
            bot.factory.addChannel(joinChannel)

    def executePart(self, bot, user, channel, message):
        if user==channel or config['users'][user]['admin']:
            bot.leave(channel, 'requested by {}'.format(user))
            del config['users']['channel']
            config['channels'].remove(channel)
            config.save()

    def executeAdd(self, bot, user, channel, message):
        if user == channel or config['users'][user]['admin']: # limit to owner of channel or admin
            cmd = message.lower().split(' ')[1]
            lookup = ['dogs','dogfacts','multi','speedrun','youtube']
            if (cmd not in lookup):
                bot.say(channel, 'I don\'t know \'{}\', choose from {}'.format(cmd, ', '.join(lookup)))
            elif not config['users'][channel][cmd]:
                config['users'][channel][cmd] = True
                config.save()
                bot.say(channel, '\'{}\' module is now active in this channel!'.format(cmd))
            else:
                bot.say(channel, '\'{}\' is already active in this channel!'.format(cmd))

    def executeDisable(self, bot, user, channel, message):
        if user == channel or config['users'][user]['admin']: # limit to owner of channel
            cmd = message.lower().split(' ')[1]
            lookup = ['dogs','dogfacts','multi','speedrun','youtube']
            if (cmd not in lookup):
                bot.say(channel, 'I don\'t know \'{}\', choose from {}'.format(cmd, ', '.join(lookup)))
            elif config['users'][channel][cmd]:
                config['users'][channel][cmd] = False
                config.save()
                bot.say(channel, '\'{}\' module is now inactive!'.format(cmd))
            else:
                bot.say(channel, '\'{}\' is already inactive in this channel!'.format(cmd))

    def executeIgnore(self, bot, user, channel, message):
        if user == channel or config['users'][user]['admin'] and not config['users'][message.split(' ')[1]]['admin']:
            if message.split(' ')[1] == "global" and config['users'][user]['admin']: 
                config['globalignorelist'].append(message.split(' ')[2].lower())
                bot.say(channel,"{} added to the global ignore list.".format(message.split(' ')[2]))
                config.save()
            else:
                config['users'][channel]['ignore'].append(message.split(' ')[1].lower())
                bot.say(channel,"{} added to this channel's ignore list.".format(message.split(' ')[1]))
                config.save()

    def executeUnignore(self, bot, user, channel, message):
        if user == channel or config['users'][user]['admin']:
            if message.split(' ')[1] == "global" and config['users'][user]['admin']: 
                config['globalignorelist'].remove(message.split(' ')[2].lower())
                bot.say(channel,"{} removed from the global ignore list.".format(message.split(' ')[2]))
                config.save()
            else:
                config['users'][channel]['ignore'].remove(message.split(' ')[1].lower())
                bot.say(channel,"{} removed to this channel's ignore list.".format(message.split(' ')[1]))
                config.save()

    def executePb(self, bot, user, channel, message):
        if not config['users'][channel]['speedrun']: return
        try:
            category = 'blank'
            cat = "blank1"
            record = message.split(' ',3)
            if len(record) <= 1: runner = channel
            elif len(record) >= 1: runner = record[1].lower()
            if len(record) <= 2 :
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                game = twitchData["game"]
            elif len(record) >= 2: game = record[2].lower()
            if len(record) == 4 : category = record[3].lower()
            url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8') + "&user=" + runner
            response = urllib.urlopen(url);
            data = self.lowerDict(json.load(response))
            if len(record) != 4:
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                for cat in config['categories']:
                    if cat in twitchData['status'].lower(): 
                        category = cat
                        break
                if 'any%' in data.values()[0].keys() and category != cat: category = 'any%'
                elif 'any%' not in data.values()[0].keys() and category != cat: category = data.values()[0].keys()[0]
            pbTime = 0
            x = [0, 0]
            value = data.values()[0][category]
            pbTime = value['time'] if 'timeigt' not in value.keys() else value['timeigt']
            if '.' in str(pbTime):
                x = float(pbTime)
                x = math.modf(x)
                pbTime = x[1]
            game = data.keys()[0]
            if int(pbTime) > 3600:
                timeString = str(datetime.timedelta(seconds=int(pbTime)))
            elif int(pbTime) < 3600:
                timeString = str(int(int(pbTime)/60)).zfill(2)+":"+str(int(pbTime)%60).zfill(2)
            if pbTime == 0:
                bot.say(channel, "The user does not have a time in this category.")
            elif pbTime != 0 and float(x[0]) == 0:
                bot.say(channel, "{}'s personal record in {} {} is {}".format(runner.title(), game.title().encode('utf8'), category.title(), timeString))
            elif pbTime != 0 and float(x[0]) != 0:
                pbDec = str(x[0])
                bot.say(channel, "{}'s personal record in {} {} is {}{}".format(runner.title(), game.title().encode('utf8'), category.title(), timeString, pbDec[1:]))
        except Exception, e:
            bot.say(channel, "Error handling request")
            print e
            print sys.exc_traceback.tb_lineno 

    def executeWrVideo(self, bot, user, channel, message):
        try:
            category = 'blank'
            cat = "blank1"
            record = message.split(' ', 3)
            if len(record) <= 2:
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                game = twitchData["game"]
            else: game = record[2].lower()
            url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8')
            response = urllib.urlopen(url)
            data = self.lowerDict(json.load(response))
            if len(record) == 4 : category = record[3].lower()
            else:
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                for cat in config['categories']:
                    if cat in twitchData['status'].lower(): 
                        category = cat
                        break
                if 'any%' in data.values()[0].keys() and category != cat: category = 'any%'
                elif 'any%' not in data.values()[0].keys() and category != cat: category = data.values()[0].keys()[0]
            game = data.keys()[0]
            video = data.values()[0][category]['video']
            bot.say(channel, "The world record video for {} {} is {}".format(game.title(), category.title(), video))
            return
        except Exception, e:
            bot.say(channel, "Error handling request")
            print e
            print sys.exc_traceback.tb_lineno 

    def executeWr(self, bot, user, channel, message):
        if not config['users'][channel]['speedrun']: return
        try:
            category = 'blank'
            cat = "blank1"
            record = message.split(' ', 2)
            if len(record) >= 2 and record[1] == 'video':
                self.executeWrVideo(bot, user, channel, message);
                return
            if len(record) <= 1:
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                game = twitchData["game"]
            if len(record) != 1: game = record[1].lower()
            if len(record) == 3 : category = record[2].lower()
            url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8')
            response = urllib.urlopen(url)
            data = self.lowerDict(json.load(response))
            if len(record) != 3:
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                for cat in config['categories']:
                    if cat in twitchData['status'].lower(): 
                        category = cat
                        break
                if 'any%' in data.values()[0].keys() and category != cat: category = 'any%'
                elif 'any%' not in data.values()[0].keys() and category != cat: category = data.values()[0].keys()[0]
            value = data.values()[0][category]
            wrTime = value['time'] if 'timeigt' not in value.keys() else value['timeigt']
            x = [0, 0]
            runner = value['player']
            game = data.keys()[0]
            if '.' in str(wrTime):
                x = float(wrTime)
                x = math.modf(x)
                wrTime = x[1]
            game = data.keys()[0]
            if int(wrTime) > 3600:
                timeString = str(datetime.timedelta(seconds=int(wrTime)))
            elif int(wrTime) < 3600:
                timeString = str(int(int(wrTime)/60)).zfill(2)+":"+str(int(wrTime)%60).zfill(2)
            if wrTime == 0:
                bot.say(channel, "The specified category doesn't exist")
            elif wrTime != 0 and float(x[0]) == 0:
                bot.say(channel, "The world record in {} {} is {} by {}.".format(game.title().encode('utf8'), category.title(), timeString, runner.title()))
            elif wrTime != 0 and float(x[0]) != 0:
                wrDec = str(x[0])
                bot.say(channel, "The world record in {} {} is {}{} by {}".format(game.title().encode('utf8'), category.title(), timeString, wrDec[1:], runner.title()))
        except Exception, e:
            bot.say(channel, "Error handling request")
            print e
            print sys.exc_traceback.tb_lineno 

    def executeSplits(self, bot, user, channel, message):
        if not config['users'][channel]['speedrun']: return
        try:
            category = 'blank'
            cat = "blank1"
            record = message.split(' ',3)
            if len(record) <= 1: runner = channel
            elif len(record) >= 1: runner = record[1].lower()
            if len(record) <= 2 :
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                game = twitchData["game"]
            elif len(record) >= 2: game = record[2].lower()
            if len(record) == 4 : category = record[3].lower()
            url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8') + "&user=" + runner
            response = urllib.urlopen(url);
            data = self.lowerDict(json.load(response))
            if len(record) != 4:
                twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
                twitchResponse = urllib.urlopen(twitchUrl);
                twitchData = json.load(twitchResponse)
                for cat in config['categories']:
                    if cat in twitchData['status'].lower(): 
                        category = cat
                        break
                if 'any%' in data.values()[0].keys() and category != cat: category = 'any%'
                elif 'any%' not in data.values()[0].keys() and category != cat: category = data.values()[0].keys()[0]
            splitid = 0
            x = [0, 0]
            value = data.values()[0][category]
            splitid = value['splitsio']
            game = data.keys()[0]
            if splitid is None:
                bot.say(channel, "The user doesn't have splits for this category on speedrun.com.")
            elif splitid != 0:
                bot.say(channel, "{}'s splits for {} {} is splits.io/{}".format(runner.title(), game.title().encode('utf8'), category.title(), splitid))
        except Exception, e:
            bot.say(channel, "Error handling request")
            print e
            print sys.exc_traceback.tb_lineno 

    def executeRace(self, bot, user, channel, message):
        if not config['users'][channel]['speedrun']: return
        try:
            splitmessage = message.split(' ')
            if len(splitmessage) == 1: splitmessage.append('kadgar')
            if len(splitmessage) >= 3: fracer = splitmessage[2]
            else: fracer = channel
            srlurl = "http://api.speedrunslive.com/races"
            srlresponse = urllib.urlopen(srlurl);
            srldata = json.load(srlresponse)
            for x in xrange(0,len(srldata['races'])):
                srlracers = []
                for k,v in srldata['races'][x]['entrants'].iteritems():
                    if splitmessage[1] == 'srl' and fracer in srldata['races'][x]['entrants'][k]['twitch']:
                        bot.say(channel, 'http://www.speedrunslive.com/race/?id={}'.format(srldata['races'][x]['id']))
                        return
                    if len(srldata['races'][x]['entrants'][k]['twitch']) != 0:
                        twitchUrl = "https://api.twitch.tv/kraken/streams/" + srldata['races'][x]['entrants'][k]['twitch'].lower()
                        twitchResponse = urllib.urlopen(twitchUrl);
                        twitchData = json.load(twitchResponse)
                        if twitchData['stream'] is not None: srlracers.append(srldata['races'][x]['entrants'][k]['twitch'].lower())
                if fracer in srlracers:
                    break
            if fracer in srlracers and splitmessage[1] in config['multitwitch'].keys(): bot.say(channel, config['multitwitch'][splitmessage[1]] + '{}'.format('/'.join(srlracers)))
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno

    def lowerDict(self,d):
        e = {}
        for k, v in d.iteritems():
            if isinstance(v, dict):
                e[k.lower()] = self.lowerDict(v)
            elif isinstance(v, str):
                e[k.lower()] = v.lower()
            else:
                e[k.lower()] = v
        return e
            
    def executeYoutube(self, bot, user, channel, video_id):
        url = "https://www.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&id={}&fields=items(id%2Csnippet(title%2CchannelTitle)%2CcontentDetails(duration)%2Cstatistics(viewCount%2ClikeCount%2CdislikeCount))&key={}".format(video_id, config["YTAuthKey"])
        response = urllib.urlopen(url)
        data = json.load(response)
        title = data['items'][0]['snippet']['title']
        videoPoster = data['items'][0]['snippet']['channelTitle']
        if user in config['usernicks']: user = config['usernicks'][user]
        bot.say(channel,'{} linked : {} by {}'.format(user, title.encode('utf8'), videoPoster.encode('utf8')))

    def executeDogs(self, bot, user, channel, message):
        if not config['users'][channel]['dogs']: return
        bot.say(channel, ' '.join(config['dogs']))

    def executeZimbabwe(self, bot, user, channel, message):
        if user == "spookas_":
            bot.say(channel, 'deeFelco')
        else:
            bot.say(channel, 'FrankerZ LilZ RalpherZ ZreknarF ZliL ZrehplaR')

    def executeRwanda(self, bot, user, channel, message):
        if user == "spookas_":
            bot.say(channel,'deeBenis')
        else:
            bot.say(channel,'FrankerZ LilZ RalpherZ ZreknarF ZliL ZrehplaR')

    def executeDjibouti(self, bot, user, channel, message):
        if user=="spookas_":
            bot.say(channel,'deeAyeSir')
        else:
            bot.say(channel,'FrankerZ LilZ RalpherZ ZreknarF ZliL ZrehplaR')

    def executeBotswana(self, bot, user, channel, message):
        if user == "spookas_":
            bot.say(channel,'deeArma')
        else:
            bot.say(channel,'FrankerZ LilZ RalpherZ ZreknarF ZliL ZrehplaR')

    def executeDogFacts(self, bot, user, channel, message):
        if not config['users'][channel]['dogfacts']: return

        with open('dogFacts.txt') as d:
            dogFacts = d.readlines()
            fact = random.choice(dogFacts).strip()
            dog1 = random.choice(config['dogs'])
            dog2 = random.choice(config['dogs'])
            if user in config['usernicks']: user = config['usernicks'][user]
            bot.say(channel, "{}: {} {} {}\r\n".format(user.title(), dog1, fact, dog2))

    def executeCustom(self, bot, user, channel, message):
        if user != channel and not config['users'][user]['admin']: return
        if message.split(' ')[1] == 'emote':
            emotes = message.split(' ')[2:]
            for emote in emotes: config['users'][channel]['custom']['emotes'][emote] = 0
            config.save()
            bot.say(channel, '{} added to emote list'.format(' '.join(emotes)))
            return
        elif message.split(' ')[1] == 'command':
            command = message.split(' ')[2]
            response = message.split(' ',3)[3]
            config['users'][channel]['custom']['commands'][command] = response
            bot.say(channel, '{} added to this channel\'s custom commands.'.format(command))
            config.save()
            return

    def executeDelCustom(self, bot, user, channel, message):
            if user != channel and user not in config['admin_channels']: return
            if message.split(' ')[1] == 'emote': del config['customEmoteCount'][channel][message.split(' ')[2]]
            elif message.split(' ')[1] == 'command': del config['customCommands'][channel][message.split(' ')[2]]
            bot.say(channel, '{} has been deleted'.format(message.split(' ')[2]))
            config.save()
            return

    def executeMultitwitch(self, bot, user, channel, message):
        if not config['users'][channel]['multi']: return
        mchannels = message.split(' ')[2:]
        multi = message.split(' ')[1]
        if multi not in config['multitwitch'].keys(): bot.say(channel, 'I don\'t know {}, choose from {}'.format(multi,','.join(config['multitwitch'].keys())))
        if channel not in mchannels: mchannels.append(channel)
        bot.say(channel, '{}{}'.format(config['multitwitch'][multi],'/'.join(set(mchannels))))

    def executeNick(self, bot, user, channel, message):
        config['usernicks'][user] = message.split(' ',1)[1]
        config.save()

    def executeCommands(self, bot, user, channel, message):
        commandL = []
        if config['users'][channel]['dogs']: commandL.append("+dogs")
        if config['users'][channel]['dogfacts']: commandL.append("dogfacts")
        if config['users'][channel]['multi']: commandL.append("+multi")
        if config['users'][channel]['speedrun']: commandL.extend(["+wr","+pb","+splits","+wr video"])
        for command in config['users'][channel]['custom']['commands'].keys(): commandL.append(command)
        bot.say(channel,"{}'s commands are : {}".format(channel,', '.join(commandL)))

    def executeAbout(self, bot, user, channel, message):
        bot.say(channel, "I'm a bot made by powderedmilk_ or something, check powderedmilk.github.io/wooferedmilk for more info.")

    def executePing(self, bot, user, channel, message):
        if config['users'][user]['admin']:
            bot.say(channel, "PONG")

    def start(self):
        reactor.callInThread(self.loop)
        
    def saveConfig(self, bot, user, channel, message):
        if config['users'][user]['admin']: config.save()

    def stop(self):
        self.die = True
        self.semaphore.release()

    def loop(self):
        while True:
            self.semaphore.acquire()
            if self.die: break
            (handler, bot, user, channel, message) = self.commandQueue.popleft()
            try:
                getattr(self, handler)(bot, user, channel, message)
            except Exception as e:
                print 'Error while handling command: ' + e.message

    ''' (prefix, handler, dispatch)
        prefix: how user calls the command
        handler: function that handles the command
        dispatch: if False, handle this function immediately (from socket thread),
                  if True, dispatch to worker thread - use for slow commands like wr lookup
    '''
    commands = [
        ('+join', 'executeJoin', False),
        ('+part', 'executePart', False),
        ('+add', 'executeAdd', False),
        ('+disable', 'executeDisable', False),
        ('+pb', 'executePb', True),
        ('+wr', 'executeWr', True),
        ('+splits','executeSplits', True),
        ('+dogs', 'executeDogs', False),
        ('+dogfacts', 'executeDogFacts', False),
        ('+multi','executeMultitwitch', False),
        ('zimbabwe', 'executeZimbabwe', False),
        ('+about', 'executeAbout', False),
        ('ping', 'executePing', False),
        ('djibouti','executeDjibouti',False),
        ('botswana','executeBotswana',False),
        ('rwanda','executeRwanda',False),
        ('+nick', 'executeNick',False),
        ('+ignore','executeIgnore',False),
        ('+unignore','executeUnignore',False),
        ('+race','executeRace',True),
        ('+new','executeCustom',False),
        ('+del','executeDelCustom',False),
        ('+delete','executeDelCustom',False),
        ('+reload','executeReload',False),
        ('+savecfg','saveConfig',False),
        ('+commands','executeCommands',False)
    ]


WooferHandler = WooferBotCommandHandler()
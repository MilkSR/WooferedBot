# coding=utf-8
import time
import re
import json
import random
import datetime
import urllib
import sys
import isodate
import math
import pytz
import BeautifulSoup
import api
import tweepy
import soundcloud
from collections import deque
from threading import Semaphore
from twisted.internet import reactor
from twisted.python.rebuild import Sensitive, rebuild
from settings import config

config.load()
while True:  
    if len(config.keys()) < 1:
        print "Waiting for config to load..."
        time.sleep(0.5)
    elif len(config.keys()) > 0:
        print "Config loaded! {} channels information loaded.".format(len(config['users'].keys()))
        break


auth = tweepy.OAuthHandler(config["twitter"]["tapikey"], config["twitter"]["tapisecret"])
auth.set_access_token(config["twitter"]["tapitoken"], config["twitter"]["tapitokensecret"])
scclient = soundcloud.Client(client_id=config['soundcloud_id'])
tapi = tweepy.API(auth)
lastMessage = 0
x = time.time()
YOUTUBE_LINK = re.compile(r"""\b(?:https?://)?(?:m\.|www\.)?youtu(?:be\.com|\.be)/(?:v/|watch/|.*?(?:embed|watch).*?v=)?([a-zA-Z0-9\-_]+)""", re.IGNORECASE)
SRC_LINK = re.compile(r"""\b(?:https?://)?(?:www\.)?speedrun\.com/run/([A-Za-z0-9]+)""", re.IGNORECASE)
TWITTER_LINK = re.compile(r"""\b(?:https?://)?(?:www\.)?twitter\.com/(?:[A-Za-z0-9_]+)?/status/([0-9]+)""", re.IGNORECASE)
FFZ_LINK = re.compile(r"""\b(?:https?://)?(?:www\.)?frankerfacez\.com/emoticons/(\d+)""", re.IGNORECASE)
SC_LINK = re.compile(r"""\b(?:https?://)?(?:www\.)?soundcloud\.com/(\S+)/(\S+)""", re.IGNORECASE)

#-----------------TODO-----------------
#A WORKING COMMAND/MESSAGE COOLDOWN
#Make a good race command
#Possible song requests
#Leaderboards command
#Make modules command show which are active
#Make it so people are only added to the config if they have personal commands
#Proper nickname system
#Fix quote count
#--------------------------------------

class WooferBotCommandHandler(Sensitive):

    def __init__(self):
        self.die = False
        self.semaphore = Semaphore(0)
        self.commandQueue = deque()



    def handleMessage(self, bot, user, channel, message):
            self.handleYoutube(bot, user, channel, message)
            self.handleSpeedrun(bot, user, channel, message)
            self.handleTwitter(bot, user, channel, message)
            self.handleFFZ(bot, user, channel, message)
            self.handleSoundCloud(bot, user, channel, message)
            self.updateBans(bot, user, channel, message)
            if user not in config['users'][channel]['ignore'] and user not in config['globalignorelist']:
                self.updateDogs(bot, channel, message)
                self.updateCustom(bot, user, channel, message)
                for (prefix, handler, dispatch) in self.commands:
                    if message.lower().startswith(prefix.format(config['users'][channel]['trigger'])):
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
                        break

    def updateDogs(self, bot, channel, message):
        global lastMessage
        for dog in config['dogs']:
            if dog in message and config['users'][channel]['dogs']:
                config['dogsc']['dogCount'][channel][dog] += 1
                if config['dogsc']['dogCount'][channel][dog] == 3:
                    # say dog name in channel
                    bot.say(channel, dog)
                    config['dogsc']['dogCount'][channel][dog] = 0

    def updateCustom(self, bot, user, channel, message):
        if user in config['users'].keys():
            for command in config['users'][user]['pcommands'].keys():
                if message.lower().startswith(command.lower()):
                    bot.say(channel, config['users'][user]['pcommands'][command])
        for command in config['users'][channel]['custom']['commands'].keys():
            if message.lower().startswith(command.lower()): 
                bot.say(channel, config['users'][channel]['custom']['commands'][command])
        for phrase in config['users'][channel]['custom']['phrases'].keys():
            if phrase in message.lower():
                bot.say(channel,"{}".format(config['users'][channel]['custom']['phrases'][phrase]))
        for emote in config['users'][channel]['custom']['emotes'].keys():
            if emote in message:
                config['users'][channel]['custom']['emotes'][emote] += 1
                if config['users'][channel]['custom']['emotes'][emote]  == 3:
                    bot.say(channel, emote)
                    config['users'][channel]['custom']['emotes'][emote] = 0
        return

    def updateBans(self, bot, user, channel, message):
        if len(config['users'][channel]['bannedwords']) == 0: return
        for i in config['users'][channel]['bannedwords'].keys():
            if i in message:
                if config['users'][channel]['bannedwords'][i] == "ban":
                    bot.say(channel,"/ban {}".format(user))
                elif type(config['users'][channel]['bannedwords'][i]) == 'int':
                    bot.say(channel,"/timeout {} {}".format(user,config['users'][channel]['bannedwords'][i]))

    # def updateLog(self, bot, channel, message):
        # if channel not in config['logging']: return
        # [channel]['log'].append(time.strftime("[%H:%M:%S]") + ' <' + user + '> ' + message)

    def handleYoutube(self, bot, user, channel, message):
        if not config['users'][channel]['linkinfo']: return
        match = YOUTUBE_LINK.search(message)
        if not match:
            return

        self.commandQueue.append(('executeYoutube', bot, user, channel, match.group(1)))
        self.semaphore.release()

    def handleSpeedrun(self, bot, user, channel, message):
        if not config['users'][channel]['speedrun']: return
        match = SRC_LINK.search(message)
        if not match:
            return
        self.commandQueue.append(('executeSRCRun', bot, user, channel, match.group(1)))
        self.semaphore.release()

    def handleTwitter(self, bot, user, channel, message):
            if not config['users'][channel]['linkinfo']: return
            match = TWITTER_LINK.search(message)
            if not match:
                return

            self.commandQueue.append(('executeTwitter', bot, user, channel, match.group(1)))
            self.semaphore.release()

    def handleSoundCloud(self, bot, user, channel, message):  
        if not config['users'][channel]['linkinfo']: return
        match = SC_LINK.search(message)
        if not match:
            return
        self.commandQueue.append(('executeSoundCloud', bot, user, channel, (match.group(1), match.group(2))))
        self.semaphore.release()

    def handleFFZ(self, bot, user, channel, message):
        if not config['users'][channel]['linkinfo']: return
        match = FFZ_LINK.search(message)
        if not match:
            return

        self.commandQueue.append(('executeFFZ', bot, user, channel, match.group(1)))
        self.semaphore.release()

    def executeFFZ(self, bot, user, channel, id):
        data = api.getFFZEmoteData(id)
        if user in config['users'].keys() and config['users'][user]['nick'] != None : user = config['users'][user]['nick']
        bot.say(channel,"{} linked: {} by {}".format(user,data['emote']['name'],data['emote']['owner']['display_name']))

    def executeTwitter(self, bot, user, channel, id):
        try:
            data = api.getTwitterData(tapi,id)
            post = data['text'].encode('utf8').replace('\n', ' ')
            bot.say(channel,"[{}:@{}] tweeted: {}".format(data['user']['name'].encode('utf8'),data['user']['screen_name'].encode('utf8'),post))
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno

    def executeSRCRun(self, bot, user, channel, run_id):
        if user in config['users'].keys() and config['users'][user]['nick'] != None : user = config['users'][user]['nick']
        data = api.getSRCRun(run_id)
        if data['data']['players']['data'][0]['rel'] == 'user': runner = data['data']['players']['data'][0]['names']['international']
        elif data['data']['players']['data'][0]['rel'] == 'guest': runner = data['data']['players']['data'][0]['name']
        game = data['data']['game']['data']['names']['international']
        category = data['data']['category']['data']['name']
        pbTime = data['data']['times']['primary_t']
        if type(data['data']['level']['data']) == dict: category = '-' + ' ' + data['data']['level']['data']['name'] + ': ' + category
        x = [0,0]
        if '.' in str(pbTime):
            x = float(pbTime)
            x = math.modf(x)
            pbTime = x[1]
        if int(pbTime) > 3600:
            timeString = str(datetime.timedelta(seconds=int(pbTime)))
        elif int(pbTime) < 3600:
            timeString = str(int(int(pbTime)/60)).zfill(2)+":"+str(int(pbTime)%60).zfill(2)
        if pbTime != 0 and float(x[0]) == 0:
            bot.say(channel, "{} linked: {} {} in {} by {}".format(user, game, category, timeString, runner))
        elif float(x[0]) != 0:
            pbDec = str(x[0])
            bot.say(channel, "{} linked: {} {} in {}{} by {}".format(user, game, category, timeString, pbDec[1:], runner))

    def executeSoundCloud(self, bot, user, channel, user_song): 
        trackURL = 'http://soundcloud.com/{}/{}'.format(user_song[0],user_song[1])
        track = api.getSCData(scclient,trackURL)
        if int(track.duration) > 60000:
            s = track.duration / 1000
            secs = s % 60
            s /= 60
            minutes = s %60
            length = str(minutes) + ":" + str(secs)
        elif int(track.duration) < 60000:
            s = track.duration / 1000
            length = "0:" + str(s % 60)
        if user in config['users'].keys() and config['users'][user]['nick'] != None : user = config['users'][user]['nick']
        bot.say(channel, "{} linked: {} uploaded by {} | Length: {} | Genre: {}".format(user,track.title.encode('utf-8'),track.user['username'],length,track.genre.encode('utf-8')))
            
    def executeJoin(self, bot, user, channel, message):
        parts = message.split(' ')
        # this command can be used in two ways:
        # 1) any user can enter +join in any of the bot admin channels,
        #    causing the bot to join the user's channel
        # 2) admins can request the bot to join anybodies channel
        #    entering +join <user>
        if len(parts) == 1 and config['users'][channel]['status'] == 'admin':
            joinChannel = user
        elif len(parts) == 2 and config['users'][user]['status'] == 'admin':
            joinChannel = parts[1]
        else:
            return # invalid syntax

        if joinChannel in config['channels']:
            bot.say(channel, '{} is already in channel #{}!'.format(config['nickname'], joinChannel))
        else:
            bot.say(channel, '{} will join #{} shortly.'.format(config['nickname'], joinChannel))
            bot.factory.addChannel(joinChannel,user)

    def executePart(self, bot, user, channel, message):
        try:
            if user==channel or config['users'][user]['status'] == 'admin':
                bot.say(channel,"Seeya LilZ /")
                bot.leave(channel, 'requested by {}'.format(user))
                del config['users'][channel]
                config['channels'].remove(channel)
                config.save()
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno

    def executeAdd(self, bot, user, channel, message):
        try:
            if user == channel or not bot.getUserMode(channel, user).is_regular() or config['users'][user]['status'] == 'admin':
                cmd = []
                newcmd = []
                notcmd = []
                activecmd = []
                cmd.extend(message.lower().split(' ')[1:])
                lookup = ['dogs','dogfacts','multi','speedrun','linkinfo','utility','quote','faqm','lastfm','novelty','pokedex']
                if config['users'][user]['status'] == 'admin': lookup.append('butt')
                for i in cmd:
                    if i == 'faq': i = 'faqm'
                    if i not in lookup:
                        notcmd.append(i)
                    elif config['users'][channel][i]:
                        activecmd.append(i)
                    elif not config['users'][channel][i]:
                        config['users'][channel][i] = True
                        newcmd.append(i)
                if len(newcmd) == 0: cmds = ""
                elif len(newcmd) > 1: cmds = "{} modules have been activated.".format(', '.join(newcmd))
                else: cmds = "{} module has been activated.".format(', '.join(newcmd))
                if len(notcmd) == 0: notcmds = ""
                elif len(notcmd) > 1: notcmds = "{} modules don't exist.".format(', '.join(notcmd))
                else: notcmds = "{} module doesn't exist.".format(', '.join(notcmd))
                if len(activecmd) == 0: activecmds = ""
                elif len(activecmd) > 1: activecmds = "{} modules were already active.".format(', '.join(activecmd))
                else: activecmds = "{} module was already active.".format(', '.join(activecmd))
                bot.say(channel,"{} {} {}".format(cmds,notcmds,activecmds))
                config.save()
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno

    def executeDisable(self, bot, user, channel, message):
        if user == channel or not bot.getUserMode(channel, user).is_regular()  or config['users'][user]['status'] == 'admin':
            cmd = message.lower().split(' ')[1]
            if cmd == 'faq': cmd = 'faqm'
            lookup = ['dogs','dogfacts','multi','speedrun','linkinfo','utility','quote','faqm','lastfm','novelty','pokedex']
            if config['users'][channel]['butt']: lookup.append('butt')
            if (cmd not in lookup):
                bot.say(channel, 'I don\'t know \'{}\', choose from {}'.format(cmd, ', '.join(lookup)))
            elif config['users'][channel][cmd]:
                config['users'][channel][cmd] = False
                config.save()
                bot.say(channel, '\'{}\' module is now inactive!'.format(cmd))
            else:
                bot.say(channel, '\'{}\' is already inactive in this channel!'.format(cmd))

    def executeIgnore(self, bot, user, channel, message):
        if user == channel or config['users'][user]['status'] == 'admin' or not bot.getUserMode(channel, user).is_regular() :
            if message.split(' ')[1] == "global" and config['users'][user]['status'] == 'admin':
                config['globalignorelist'].append(message.split(' ')[2].lower())
                bot.say(channel,"{} added to the global ignore list.".format(message.split(' ')[2]))
                config.save()
            else:
                config['users'][channel]['ignore'].append(message.split(' ')[1].lower())
                bot.say(channel,"{} added to this channel's ignore list.".format(message.split(' ')[1]))
                config.save()

    def executeUnignore(self, bot, user, channel, message):
        if user == channel or not bot.getUserMode(channel, user).is_regular()  or config['users'][user]['status'] == 'admin':
            if message.split(' ')[1] == "global" and config['users'][user]['status'] == 'admin':
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
            cat = "x"
            category = "y"
            x = [0,0]
            if len(message.split(' ')) >= 2:
                runner = message.split(' ')[1]
                idData = api.getSRCIDData("pb","lookup=" + runner)
                uid = idData['data'][0]['id']
                runner = idData['data'][0]['names']['international']
            else:
                idData = api.getSRCIDData("pb", "twitch=" + channel)
                uid = idData['data'][0]['id']
                runner = idData['data'][0]['names']['international']
            if len(message.split(' ')) <= 2: game = api.getTwitchData(channel)['game']
            else: game = message.split(' ')[2]
            gdata = api.getSRCNAData(game,"wr","")
            if gdata['data'] == []: gdata = api.getSRCNFData(game, "wr","")
            game = gdata['data'][0]['id']
            data = api.getSRCUData(uid,game)['data']
            categoryData = api.getSRCNCategories(gdata['data'][0]['links'][4]['uri'])
            if len(message.split(' ')) <= 3:
                twitchData = api.getTwitchData(channel)
                for cat in categoryData['data']:
                    if cat['name'].lower() in twitchData['status'].lower():
                        category = cat['name']
                        cat = category
                        break
            elif len(message.split(' ')) >= 4: category = message.split(' ',3)[3]
            for d in data:
                if d['category']['data']['name'].lower() == category.lower():
                    category = d['category']['data']['name']
                    run = d
                    break
            if category == "y":
                run = data[0]
                category = run['category']['data']['name']
            game = data[0]['game']['data']['names']['international']
            pbTime = run['run']['times']['primary_t']
            page = run['run']['weblink']
            if '.' in str(pbTime):
                x = float(pbTime)
                x = math.modf(x)
                pbTime = x[1]
            if int(pbTime) > 3600:
                timeString = str(datetime.timedelta(seconds=int(pbTime)))
            elif int(pbTime) < 3600:
                timeString = str(int(int(pbTime)/60)).zfill(2)+":"+str(int(pbTime)%60).zfill(2)
            if pbTime == 0 and float(x[0]) == 0:
                bot.say(channel, "The specified category doesn't exist")
            elif pbTime != 0 and float(x[0]) == 0:
                bot.say(channel, "{}'s personal record in {} {} is {} | Run Page: {}".format(runner, game, category, timeString, page))
            elif float(x[0]) != 0:
                pbDec = str(x[0])
                bot.say(channel, "{}'s personal record in {} {} is {}{} | Run Page: {}".format(runner, game, category, timeString, pbDec[1:], page))
        except Exception, e:
            bot.say(channel, "Error handling request")
            print e
            print sys.exc_traceback.tb_lineno

    def executeWr(self, bot, user, channel, message):
        start = time.time()
        if not config['users'][channel]['speedrun']: return
        try:
            g = 0
            cat = "x"
            category = "y"
            possibleCategories = []
            x = [0,0]
            if len(message.split(' ')) == 1: game = api.getTwitchData(channel)['game'].encode("utf8")
            else: game = ' '.join(message.split(' ',1)[1:])
            data = api.getSRCNAData(game,"wr","")
            if len(data['data']) < 1: data = api.getSRCNFData(game, "wr","")
            while len(data['data']) < 1:
                if type(game) == str: game = game.split(' ')
                game.remove(game[len(game)-1])
                if len(game) < 1:
                    break
                game = ' '.join(game)
                data = api.getSRCNAData(game,"wr","")
            if len(data['data']) < 1 and len(game) < 1: game = ' '.join(message.split(' ',1)[1:])
            while len(data['data']) < 1:
                if type(game) == str: game = game.split(' ')
                game.remove(game[len(game)-1])
                if len(game) < 1:
                    bot.say(channel,"Game could not be found.")
                    return
                data = api.getSRCNFData(game, "wr","")
            if len(game) > 1 and type(game) == list:
                igame = ' '.join(game)
            elif type(game) == str: 
                igame = game
            game = data['data'][0]['names']['international']
            categoryData = api.getSRCNCategories(data['data'][0]['links'][4]['uri'])
            if len(message.split(' ')) <= 2 or message.split(' ',1)[1] == igame:
                print 'there probably wasn\'t a category given'
                twitchData = api.getTwitchData(channel)
                for cat in categoryData['data']:
                    if cat['name'].lower() in twitchData['status'].lower():
                        possibleCategories.append(cat['name'])
                    if len(possibleCategories) > 0: 
                        category = max(possibleCategories,key=len)
                        cat = category
                if category != cat:
                    link = data['data'][0]['links'][8]['uri'] + "?embed=category,players,variables&top=1"
                else:
                    link = data['data'][0]['links'][4]['uri']
                    cData = api.getSRCNCategories(link)
                    for c in cData['data']:
                        if c['type'] == "per-game" and c['name'].lower() == category.lower(): link = c['links'][5]['uri'] + "?embed=category,players,variables&top=1"
            else:
                message = message.lower().split(' ')
                message.remove('+wr')
                for g in igame.split(' '):
                    message.remove(g.lower())
                category = ' '.join(message)
                link = data['data'][0]['links'][4]['uri']
                cData = api.getSRCNCategories(link)
                for c in cData['data']:
                    if c['type'] == "per-game" and c['name'].lower() == category.lower():
                        link = c['links'][5]['uri']  + "?embed=category,players&top=1"
                        break
            lbdata = api.getSRCNLeaderboard(link)
            category = lbdata['data']['category']['data']['name']
            wrTime = lbdata['data']['runs'][0]['run']['times']['primary_t']
            page = lbdata['data']['runs'][0]['run']['weblink']
            if lbdata['data']['players']['data'][0]['rel'] == 'user': runner = lbdata['data']['players']['data'][0]['names']['international']
            elif lbdata['data']['players']['data'][0]['rel'] == 'guest': runner = lbdata['data']['players']['data'][0]['name']
            if len(lbdata['data']['players']['data']) > 1: runner = runner + " ({}-way tie)".format(str(len(lbdata['data']['players']['data'])))
            if '.' in str(wrTime):
                x = float(wrTime)
                x = math.modf(x)
                wrTime = x[1]
            if int(wrTime) > 3600:
                timeString = str(datetime.timedelta(seconds=int(wrTime)))
            elif int(wrTime) < 3600:
                timeString = str(int(int(wrTime)/60)).zfill(2)+":"+str(int(wrTime)%60).zfill(2)
            if user in config['users'].keys() and config['users'][user]['status'] == 'admin': 
                rtime = " ({} seconds)".format(str(time.time() - start)[:4])
            else: rtime = ""
            if wrTime == 0 and float(x[0]) == 0:
                bot.say(channel, "The specified category doesn't exist")
            elif wrTime != 0 and float(x[0]) == 0:
                bot.say(channel, "The world record in {} {} is {} by {} | Run Page: {}{}".format(game.encode('utf8'), category, timeString, runner, page, rtime))
            elif float(x[0]) != 0:
                wrDec = str(x[0])
                bot.say(channel, "The world record in {} {} is {}{} by {} | Run Page: {}{}".format(game.encode('utf8'), category, timeString, wrDec[1:], runner, page, rtime))
        except Exception, e:
            bot.say(channel, "Error handling request")
            print e
            print sys.exc_traceback.tb_lineno

#    def executeRace(self, bot, user, channel, message):
#        if not config['users'][channel]['speedrun']: return
#        try:
#            splitmessage = message.split(' ')
#            if len(splitmessage) == 1: splitmessage.append('kadgar')
#            if len(splitmessage) >= 3: fracer = splitmessage[2]
#            else: fracer = channel
#            srldata = api.getSRLData()
#            for x in xrange(0,len(srldata['races'])):
#                srlracers = []
#                for k,v in srldata['races'][x]['entrants'].iteritems():
#                    if splitmessage[1] == 'srl' and fracer in srldata['races'][x]['entrants'][k]['twitch']:
#                        bot.say(channel, 'http://www.speedrunslive.com/race/?id={}'.format(srldata['races'][x]['id']))
#                        return
#                    if len(srldata['races'][x]['entrants'][k]['twitch']) != 0:
#                        twitchData = api.getTwitchData(srldata['races'][x]['entrants'][k]['twitch'].lower())
#                        if twitchData['stream'] is not None: srlracers.append(srldata['races'][x]['entrants'][k]['twitch'].lower())
#                if fracer in srlracers:
#                    break
#            if fracer in srlracers and splitmessage[1] in config['multitwitch'].keys(): bot.say(channel, config['multitwitch'][splitmessage[1]] + '{}'.format('/'.join(srlracers)))
#        except Exception,e:
#            print e
#            print sys.exc_traceback.tb_lineno

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
        data = api.getYouTubeData(video_id)
        title = data['items'][0]['snippet']['title']
        videoPoster = data['items'][0]['snippet']['channelTitle']
        if user in config['users'].keys() and config['users'][user]['nick'] != None : user = config['users'][user]['nick']
        bot.say(channel,'{} linked: {} by {}'.format(user, title.encode('utf8'), videoPoster.encode('utf8')))

    def executeSet(self, bot, user, channel, message):
        if user == channel or config['users'][user]['status'] == 'admin':
            if message.split(' ')[1] == 'trigger': config['users'][channel]['trigger'] = message.split(' ')[2].strip()
            if message.split(' ')[2] == 'admin' and user == 'powderedmilk_':
                config['users'][message.split(' ')[1]]['status'] = 'admin'
                bot.say(channel,"{} set as bot admin".format(message.split(' ')[1]))
            if message.split(' ')[1] == 'cooldown': config['users'][channel]['cooldowns'][message.split(' ')[2]] = message.split(' ')[3]
            config.save()

    def executeDogs(self, bot, user, channel, message):
        if not config['users'][channel]['dogs']: return
        i = random.randint(0,1000)
        if i == 89:
            bot.say(channel,"ChefFrank You have been visited by Chef Frank, good dog biscuits and happiness will come your way")
            return
        bot.say(channel, ' '.join(config['dogs']))

    def dag(self, bot, user, channel, message):
        if not config['users'][channel]['dogs']: return
        bot.say(channel, "{}".format(random.choice(config['dogs'])))

    def executeSlots(self, bot, user, channel, message):
        if not config['users'][channel]['novelty']: return
        if user != "powderedmilk_":
            d1 = random.choice(config['dogs'])
            d2 = random.choice(config['dogs'])
            d3 = random.choice(config['dogs'])
        else:
            d1 = random.choice(config['dogs'])
            d2 = d1
            d3 = d2
        bot.say(channel,"{} {} {}".format(d1,d2,d3))
        time.sleep(1.5)
        if d1 == d2 and d2 == d3: bot.say(channel,"Jackpot {}".format(d1))

    def executeEightBall(self, bot, user, channel, message):
        if not config['users'][channel]['novelty']: return
        bot.say(channel,random.choice(config['8ball']))

    def executeDogFacts(self, bot, user, channel, message):
        if not config['users'][channel]['dogfacts']: return

        with open('dogFacts.txt') as d:
            dogFacts = d.readlines()
            fact = random.choice(dogFacts).strip()
            dog1 = random.choice(config['dogs'])
            dog2 = random.choice(config['dogs'])
            if user in config['users'].keys() and config['users'][user]['nick'] != None : user = config['users'][user]['nick']
            bot.say(channel, "{}: {} {} {}\r\n".format(user, dog1, fact, dog2))

    def executeCustom(self, bot, user, channel, message):
        if user != channel and bot.getUserMode(channel, user).is_regular() and not config['users'][user]['status'] == 'admin': return
        if message.split(' ')[1].lower() == 'emote':
            emotes = message.split(' ')[2:]
            for emote in emotes: config['users'][channel]['custom']['emotes'][emote] = 0
            bot.say(channel, '{} added to emote list'.format(' '.join(emotes)))
        elif message.split(' ')[1].lower() == 'command':
            command = message.split(' ')[2]
            response = message.split(' ',3)[3]
            config['users'][channel]['custom']['commands'][command] = response
            bot.say(channel, '{} added to this channel\'s custom commands.'.format(command))
        elif message.split(' ')[1].lower() == 'quote' and config['users'][channel]['quote']:
            if not message.split(' ')[2].startswith('"'): 
                qid = message.split(' ')[2]
                length = 3
            else:
                for x in xrange(0,1000):
                    if str(x) not in config['users'][channel]['quotes'].keys():
                        qid = x
                        length = 2
                        break
            quote = message.split(' ',length)[length]
            config['users'][channel]['quotes'][qid] = quote
            bot.say(channel,"{} added to the this channels quote list with the id:{}".format(quote,qid))
        elif message.split(' ')[1].lower() == 'faq' and (user == channel or config['users'][user]['status'] == 'admin'):
            game = api.getTwitchData(channel)['game'].encode("utf8")
            faq = message.split(' ',2)[2].encode("utf8")
            config['users'][channel]['faq'][game] = faq
            bot.say(channel,"{}'s FAQ set to {}".format(game,faq))
        elif message.split(' ')[1].lower() == 'global' and config['users'][user]['status'] == 'admin':
            command = message.split(' ')[3].lower()
            cuser = message.split(' ')[2]
            if cuser not in config['users'].keys():
                config['users'][cuser] = {}
                config['users'][cuser]['status'] = 'chatter'
                config['users'][cuser]['pcommands'] = {}
            response = message.split(' ',4)[4]
            config['users'][cuser]['pcommands'][command] = response
            print config['users'][cuser]['pcommands'].keys()
            bot.say(channel, "{} can now use {}!".format(cuser,command))
        elif message.split(' ')[1].lower() == "phrase":
            message = message.split(',',1)
            phrase = message[0].split(' ',2)[2].lower()
            reply = message[1]
            config['users'][channel]['custom']['phrases'][phrase] = reply
            bot.say(channel,"{} added to to this channel\'s list of phrases.".format(phrase))
        config.save()
        config.load()
        print 'config saved'
        return

    def setLastfmAccount(self, bot, user, channel, message):
        if user != channel and not config['users'][user]['status'] == 'admin': return
        config['users'][channel]['lastfma'] = message.split(' ')[1]
        bot.say(channel,"last.fm account set to {}".format(message.split(' ')[1]))
        config.save()

    def getSong(self, bot, user, channel, message):
        if not config['users'][channel]['lastfm']: return
        try:
            if len(config['users'][channel]['lastfma']) > 0:
                data =api.getLastfmData(config['users'][channel]['lastfma'])
                rt = data['recenttracks']['track'][0]
                if len(rt['album']['#text']) > 0: album = "from the album \"{}\"".format(rt['album']['#text'].encode("utf8"))
                else: album = ""
                bot.say(channel,"The current song is \"{}\" by {} {}".format(rt['name'].encode('utf8'),rt['artist']['#text'].encode('utf8'),album))
            else: bot.say(channel,"You need to set a last.fm account name in the bot before using this command")
            return
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno

    def getPokemonData(self, bot, user, channel, message):
        if not config['users'][channel]['pokedex']: return
        try:
            pokemon = message.split(' ',1)[1].lower()
            data = api.getPokedex()
            for i in data['pokemon']:
                if i['name'] == pokemon:
                    apiEnd = i['resource_uri']
                    break
            pkmnData = api.getPokemon(apiEnd)
            name = pkmnData['name']
            if name == "Mr-mime": name = "Mr. Mime"
            elif name == "Mime-jr": name = "Mime Jr."
            natID = pkmnData['national_id']
            species = ', the {} Pokémon'.format(config['pkmnspecies'][name])
            hp = pkmnData['hp']
            a  = pkmnData['attack']
            d = pkmnData['defense']
            sa = pkmnData['sp_atk']
            sd = pkmnData['sp_def']
            s = pkmnData['speed']
            types = []
            for t in pkmnData['types']:
                types.append(t['name'])
            if len(types) > 1: types = "Types: {}".format(", ".join(types)).title()
            elif len(types) == 1: types = "Type: {}".format(types[0].title())
            bot.say(channel,"Pokémon #{}:{}{} | HP:{}, Atk:{}, Def:{}, Sp. Atk:{}, Sp. Def:{}, Spe:{} | {}".format(natID, name, species, hp, a, d, sa, sd, s, types))
        except Exception,e:
            print e
            bot.say(channel,"Error finding Pokémon. Make sure you spelled the Pokémon's name correctly. If it has a space in the name (ex:Mr. Mime) use Mr-Mime.")
            print sys.exc_traceback.tb_lineno

    def getEmotes(self, bot, user, channel, message):
        if len(config['users'][channel]['custom']['emotes'].keys()) <= 0: return
        bot.say(channel, "{}".format(" , ".join(config['users'][channel]['custom']['emotes'].keys())))

    def randomButt(self, bot, user, channel, message):
        if not config['users'][channel]['butt']: return
        tags = random.choice(['panties','bike_shorts'])
        page = random.randint(1,362)
        data = api.getButt(page)
        d = random.choice(data)
        bot.say(channel,"FrankerZ http://danbooru.donmai.us/posts/{}".format(d['id']))

    def executeDelCustom(self, bot, user, channel, message):
            if user != channel and bot.getUserMode(channel, user).is_regular() and not config['users'][user]['status'] == 'admin': return
            if message.split(' ')[1] == 'emote':
                del config['users'][channel]['custom']['emotes'][message.split(' ')[2]]
                bot.say(channel, '{} has been deleted'.format(message.split(' ')[2]))
            elif message.split(' ')[1] == 'command':
                del config['users'][channel]['custom']['commands'][message.split(' ')[2]]
                bot.say(channel, '{} has been deleted'.format(message.split(' ')[2]))
            elif message.split(' ')[1] == 'quote':
                del config['users'][channel]['quotes'][message.split(' ')[2]]
                bot.say(channel, "Quote {} has been deleted!".format(message.split(' ')[2]))
            elif message.split(' ')[1] == 'faq':
                game = api.getTwitchData(channel)['game']
                del config['users'][channel]['faq'][game]
                bot.say(channel, "FAQ for {} has been deleted.".format(game))
            elif message.split(' ')[1] == 'phrase':
                del config['users'][channel]['custom']['phrases'][message.split(' ',2)[2]]
                bot.say(channel,"The phrase {} has been deleted from this channel\'s list of phrases!".format(message.split(' ',2)[2]))
            config.save()
            return

    def randomQuote(self, bot, user, channel, message):
        if not config['users'][channel]['quote']: return
        if len(message.split(' ')) == 1: qid = random.choice(config['users'][channel]['quotes'].keys())
        elif len(message.split(' ')) == 2 and message.split(' ')[1] != 'count' : qid = message.split(' ')[1]
        elif len(message.split(' ')) == 2 and message.split(' ')[1] == 'count':
            bot.say(channel,"Current quote count is {}".format(len(config['users'][channel]['quotes'].keys())))
            return
        print config['users'][channel]['quotes'][qid]
        bot.say(channel, "#{}: {}".format(qid,config['users'][channel]['quotes'][str(qid)]))

    def executeMultitwitch(self, bot, user, channel, message):
        if not config['users'][channel]['multi']: return
        mchannels = message.split(' ')[2:]
        multi = message.split(' ')[1].lower()
        if multi not in config['multitwitch'].keys(): bot.say(channel, 'I don\'t know {}, choose from {}'.format(multi,', '.join(config['multitwitch'].keys())))
        if channel not in mchannels: mchannels.append(channel)
        if multi != "twitchdeck": link = "/"
        else: link = "&"
        bot.say(channel, '{}{}'.format(config['multitwitch'][multi],link.join(set(mchannels))))

    def executeNick(self, bot, user, channel, message):
        try:
            if user not in config['users'].keys():
                config['users'][user] = {}
                config['users'][user]['status'] = 'chatter'
                config['users'][user]['nick'] = None
            if len(message.split(' ',1)[1]) <= 25: config['users'][user]['nick'] = message.split(' ',1)[1]
            else:
                bot.say(channel,"Nick too long, please be sure it's under 25 characters")
                return
            bot.say(channel,"{}'s nick set to {}.".format(user,config['users'][user]['nick']))
            config.save()
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno

    def customFAQ(self, bot, user, channel, message):
        if not config['users'][channel]['faqm']: return
        game = api.getTwitchData(channel)['game'].encode("utf8")
        if game in config['users'][channel]['faq'].keys(): bot.say(channel,"The FAQ for {} is {}".format(game,config['users'][channel]['faq'][game]))
        else: bot.say(channel,"{} doesn't have a set FAQ in this channel, type {}new faq FAQ-link to set it for this game".format(game, config['users'][channel]['trigger']))

    def executeCommands(self, bot, user, channel, message):
        #Could probably still clean this up a bit, but it's a lot better
        try:    
            t = config['users'][channel]['trigger']
            commandL = []
            if user == channel or not bot.getUserMode(channel,user).is_regular() or (user in config['users'].keys() and config['users'][user]['status'] == 'admin'): commandL.extend("{}help {}about".format(t,t).split(' '))
            if config['users'][channel]['dogs']: commandL.extend("{}dogs".format(t,t).split(' '))
            if config['users'][channel]['dogfacts']: commandL.append("{}dogfacts".format(t))
            if config['users'][channel]['multi']: commandL.append("{}multi".format(t))
            if config['users'][channel]['speedrun']: commandL.extend("{}wr {}pb".format(t,t).split(' '))
            if config['users'][channel]['utility']: 
                commandL.extend("{}uptime {}title".format(t,t).split(' '))
                if user==channel or not bot.getUserMode(channel, user).is_regular() or (user in config['users'] and config['users'][user]['status'] == "admin"): commandL.extend("{}hl {}dhl {}highlights".format(t,t,t).split(' '))
            if config['users'][channel]['quote']: commandL.append("{}quote".format(t))
            if config['users'][channel]['faqm']: commandL.append("{}faq".format(t))
            if config['users'][channel]['novelty']: commandL.append("{}8ball {}slots".format(t,t))
            if config['users'][channel]['pokedex']: commandL.append("{}pkdx".format(t))
            if config['users'][channel]['lastfm']: 
                commandL.append("{}song".format(t))
                if user == channel or (user in config['users'] and config['users'][user]['status'] == 'admin'): commandL.append("{}lastfm".format(t))
            for command in config['users'][channel]['custom']['commands'].keys(): commandL.append(command)
            if user==channel or (user in config['users'].keys() and config['users'][user]['status'] == 'admin') or not bot.getUserMode(channel, user).is_regular():commandL.extend("{}enable {}disable {}modules".format(t,t,t).split(' '))
            if user == channel or (user in config['users'].keys() and config['users'][user]['status'] == 'admin'): commandL.append("{}part".format(t))
            if user in config['users']: commandL.extend(config['users'][user]['pcommands'].keys())
            commandL = list(set(commandL))
            bot.say(channel,"Your available commands in this channel are: {}".format(', '.join(commandL)))
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno

    def executeModules(self, bot, user, channel, message):
        mod = ['dogs','dogfacts','multi','speedrun','linkinfo','utility','quote','faqm','lastfm','novelty','pokedex']
        mod2 = []
        for x in mod:
            if config['users'][channel][x]: 
                if x == 'faqm': x = 'faq'
                mod2.append(x + ":✓")
            else: 
                if x == 'faqm': x = 'faq'
                mod2.append(x + ":✗")
        bot.say(channel,"Available modules are: {}.".format(', '.join(mod2)))

    def executeHelp(self, bot, user, channel, message):
        t = config['users'][channel]['trigger']
        if user != channel and channel != config['nickname'] and not config['users'][user]['status'] == 'admin' and bot.getUserMode(channel, user).is_regular(): return
        parts = message.split(' ')
        if len(parts) == 2 and t in parts[1]: parts[1] = parts[1][1:]
        if len(parts) == 1: bot.say(channel,"This command is used to explain commands, for an explanation of a command do {}help <command> (without the brackets). Example: {}help commands - If you can't figure something out, feel free to tweet @powderedmilk_ for help. ".format(t,t,t,t))
        elif len(parts) == 2 and parts[1] in config['commands'].keys(): bot.say(channel,config['commands'][parts[1]].format(t))
        elif len(parts) == 2 and parts[1] in config['users'][channel]['custom']['commands'].keys() or "{}{}".format(t,parts[1]) in config['users'][channel]['custom']['commands'].keys(): bot.say(channel, "This is a custom command in this channel, to delete it type {}del command command-name".format(t))
        else: bot.say(channel, "That command isn't available or doesn't have a description, type {}commands to see available commands.".format(t))
        print "{}{}".format(t,parts[1])

    def executeAbout(self, bot, user, channel, message):
        t = config['users'][channel]['trigger']
        bot.say(channel, "I'm a bot made by powderedmilk_ or something, use {}help for more info or go here: milksr.tk/wooferedmilk If you can't figure something out, feel free to tweet @powderedmilk_ for help. [Bot Last Updated: March 14th, 2016]".format(t))

    def executeUptime(self, bot, user, channel, message):
        if not config['users'][channel]['utility']: return
        l = api.getLiveSince(bot, user, channel)
        if l is not 0: bot.say(channel, "{} has been live for {}".format(channel,str(l)[:-7]))
        else: bot.say(channel,"{} is not currently live".format(channel))

    def executeTitle(self, bot, user, channel, message):
        if not config['users'][channel]['utility']: return
        data = api.getTwitchData(channel)
        bot.say(channel,data['status'].encode('utf8'))

    def addHighlight(self, bot, user, channel, message):
        if user == channel or not bot.getUserMode(channel, user).is_regular()  or config['users'][user]['status'] == 'admin':
            liveSince = str(api.getLiveSince(bot,user,channel))[:-7]
            if liveSince is not "0" and len(message.split(' ',1)) == 2:
                config['users'][channel]['highlights'].append(liveSince + ' "{}"'.format(message.split(' ',1)[1]))
                bot.say(channel,"{} added to highlight list".format(liveSince))
                config.save()
            elif liveSince is not "0" and len(message.split(' ',1)) == 1:
                config['users'][channel]['highlights'].append(liveSince)
                bot.say(channel,"{} added to highlight list".format(liveSince))
                config.save()

    def returnHighlights(self, bot, user, channel, message):
        if user != channel and not config['users'][user]['status'] == 'admin': return
        bot.say(channel,"The timestamps for the highlights of your last broadcast are {}".format(', '.join(config['users'][channel]['highlights'])))

    def delHighlights(self, bot, user, channel, message):
        if user != channel and not config['users'][user]['status'] == 'admin': return
        config['users'][channel]['highlights'] = []
        bot.say(channel,"Highlight timestamps deleted.")
        config.save()

    def voteBan(self, bot, user, channel, message):
        try:
            if not config['users'][channel]['voteban']: return
            buser = message.split(' ')[1].lower()
            if not bot.getUserMode(channel, buser).is_regular() or buser == channel: return
            if buser not in config['users'][channel]['votebans']: config['users'][channel]['votebans'][buser] = []
            if user not in config['users'][channel]['votebans'][buser]:
                config['users'][channel]['votebans'][buser].append(user)
            else: return
            if len(config['users'][channel]['votebans'][buser]) >= 7:
                bot.say(channel,"/timeout {}".format(buser))
                bot.say(channel,"RIP my nigga {}. Everyone pour one out.".format(buser))
                del(config['users'][channel]['votebans'][buser])
            else:
                bot.say(channel, "{} needs {} more votes to get banned for 10 minutes.".format(buser, (7 - len(config['users'][channel]['votebans'][buser]))))
            config.save()
        except Exception,e:
            print e
            print sys.exc_traceback.tb_lineno
            
    def executeUserBase(self, bot, user, channel, message):
        if not config['users'][user]['status'] == 'admin': return
        if message.startswith('+chatters'): bot.say(channel,str(len(config['users'].keys())))
        elif message.startswith('+users'): bot.say(channel,str(len(config['channels'])))

    def getAdmins(self, bot, user, channel, message):
        if not user == channel and not config['users'][user]['status'] == 'admin': return
        admins = []
        for user in config['users'].keys():
            if config['users'][user]['status'] == 'admin': admins.append(user.title())
        bot.say(channel,"{}".format(', '.join(admins)))

    def getIgnored(self, bot, user, channel, message):
        if user in config['users'].keys() and config['users'][user]['status'] == 'admin':
            bot,say(channel,"{} are ignored in this channel. {} are globally ignored".format(', '.join(config['users'][channel]['ignore']), ', '.join(config['globalignorelist'])))
        elif user == channel or not bot.getUserMode(channel, user).is_regular():
            bot,say(channel,"{} are ignored in this channel. {} are globally ignored".format(', '.join(config['users'][channel]['ignore'])))

    def start(self):
        reactor.callInThread(self.loop)

    def saveConfig(self, bot, user, channel, message):
        if config['users'][user]['status'] == 'admin':
            config.save()
            bot.say(channel,"Config file saved and sanitized")

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
        ('{}part', 'executePart', False),
        ('{}add', 'executeAdd', False),
        ('{}disable', 'executeDisable', False),
        ('{}enable','executeAdd',False),
        ('{}pb', 'executePb', True),
        ('{}wr', 'executeWr', True),
        ('{}dogs', 'executeDogs', False),
        ('{}dogfacts', 'executeDogFacts', False),
        ('{}multi','executeMultitwitch', False),
        ('{}about', 'executeAbout', False),
        ('{}nick', 'executeNick',False),
        ('{}ignore','executeIgnore',True),
        ('{}unignore','executeUnignore',True),
        ('{}race','executeRace',True),
        ('{}new','executeCustom',False),
        ('{}del','executeDelCustom',False),
        ('{}delete','executeDelCustom',False),
        ('{}reload','executeReload',False),
        ('+savecfg','saveConfig',False),
        ('{}commands','executeCommands',False),
        ('+users','executeUserBase',False),
        ('+chatters','executeUserBase',False),
        ('{}set','executeSet',False),
        ('{}admins','getAdmins',False),
        ('{}uptime','executeUptime',True),
        ('{}hl','addHighlight',True),
        ('{}dhl','delHighlights',False),
        ('{}highlights','returnHighlights',False),
        ('{}modules','executeModules',False),
        ('{}help','executeHelp', False),
        ('{}faq', 'customFAQ', False),
        ('{}slots', 'executeSlots', False),
        ('{}quote', 'randomQuote', False),
        ('{}butt', 'randomButt', True),
        ('{}lastfm','setLastfmAccount',False),
        ('{}song','getSong',True),
        ('{}8ball','executeEightBall',False),
        ('{}title','executeTitle',True),
        ('{}pkmninfo','getPokemonData', True),
        ('{}pkdx','getPokemonData',True),
        ('{}pokedex','getPokemonData',True),
        ('{}emotes','getEmotes', False),
        ('{}dance','dance',False),
        ('{}voteban','voteBan',False),
        ('{}dag','dag',False),
        ('{}ignorelist','getIgnored',False)
    ]


WooferHandler = WooferBotCommandHandler()

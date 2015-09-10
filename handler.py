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
from collections import deque
from threading import Semaphore
from twisted.internet import reactor
from twisted.python.rebuild import Sensitive, rebuild
from settings import config

YOUTUBE_LINK = re.compile(r"""\b(?:https?://)?(?:m\.|www\.)?youtu(?:be\.com|\.be)/(?:v/|watch/|.*?(?:embed|watch).*?v=)?([a-zA-Z0-9\-_]+)""")
SRC_LINK = re.compile(r"""\b(?:https?://)?(?:www\.)?speedrun\.com/run/([A-Za-z0-9]+)""")

#--------------TODO--------------
#Random SRL Host
#Chat logging
#Clean up speedrun garbage
#Mod logging
#Global Individual Commands

class WooferBotCommandHandler(Sensitive):
    def __init__(self):
        self.die = False
        self.semaphore = Semaphore(0)
        self.commandQueue = deque()

    def handleMessage(self, bot, user, channel, message):
            self.handleYoutube(bot, user, channel, message)
            self.handleSpeedrun(bot, user, channel, message)
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

    def updateDogs(self, bot, channel, message):
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
                if message.lower().startswith(command.lower()): bot.say(channel, config['users'][user]['pcommands'][command])
        for command in config['users'][channel]['custom']['commands'].keys():
            if message.lower().startswith(command.lower()): bot.say(channel, config['users'][channel]['custom']['commands'][command])
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

    def handleSpeedrun(self, bot, user, channel, message):
        if not config['users'][channel]['speedrun']: return
        match = SRC_LINK.search(message)
        if not match:
            return
        self.commandQueue.append(('executeSRCRun', bot, user, channel, match.group(1)))
        self.semaphore.release()

    def executeSRCRun(self, bot, user, channel, run_id):
        if user in config['usernicks']: user = config['usernicks'][user]
        data = api.getSRCRun(run_id)
        if data['data']['players']['data'][0]['rel'] == 'user': runner = data['data']['players']['data'][0]['names']['international']
        elif data['data']['players']['data'][0]['rel'] == 'guest': runner = data['data']['players']['data'][0]['name']
        game = data['data']['game']['data']['names']['international']
        category = data['data']['category']['data']['name']
        pbTime = data['data']['times']['primary_t']
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
            bot.factory.addChannel(joinChannel)

    def executePart(self, bot, user, channel, message):
        if user==channel or config['users'][user]['admin']:
            bot.say(channel,"Seeya LilZ /")
            bot.leave(channel, 'requested by {}'.format(user))
            del config['users'][channel]
            config['channels'].remove(channel)
            config.save()

    def executeAdd(self, bot, user, channel, message):
        config.updateModList(channel)
        if user == channel or user in config['users'][channel]['mods'] or config['users'][user]['admin']:
            cmd = message.lower().split(' ')[1]
            lookup = ['dogs','dogfacts','multi','speedrun','youtube','utility','quote']
            if (cmd not in lookup):
                bot.say(channel, 'I don\'t know \'{}\', choose from {}'.format(cmd, ', '.join(lookup)))
            elif not config['users'][channel][cmd]:
                config['users'][channel][cmd] = True
                config.save()
                bot.say(channel, '\'{}\' module is now active in this channel!'.format(cmd))
            else:
                bot.say(channel, '\'{}\' is already active in this channel!'.format(cmd))

    def executeDisable(self, bot, user, channel, message):
        config.updateModList(channel)
        if user == channel or user in config['users'][channel]['mods'] or config['users'][user]['admin']:
            cmd = message.lower().split(' ')[1]
            lookup = ['dogs','dogfacts','multi','speedrun','youtube','utility','quote']
            if (cmd not in lookup):
                bot.say(channel, 'I don\'t know \'{}\', choose from {}'.format(cmd, ', '.join(lookup)))
            elif config['users'][channel][cmd]:
                config['users'][channel][cmd] = False
                config.save()
                bot.say(channel, '\'{}\' module is now inactive!'.format(cmd))
            else:
                bot.say(channel, '\'{}\' is already inactive in this channel!'.format(cmd))

    def executeIgnore(self, bot, user, channel, message):
        config.updateModList(channel)
        if user == channel or config['users'][user]['admin'] or user in config['users'][channel]['mods']:
            if message.split(' ')[1] == "global" and config['users'][user]['admin']:
                config['globalignorelist'].append(message.split(' ')[2].lower())
                bot.say(channel,"{} added to the global ignore list.".format(message.split(' ')[2]))
                config.save()
            else:
                config['users'][channel]['ignore'].append(message.split(' ')[1].lower())
                bot.say(channel,"{} added to this channel's ignore list.".format(message.split(' ')[1]))
                config.save()

    def executeUnignore(self, bot, user, channel, message):
        config.updateModList(channel)
        if user == channel or user in config['users'][channel]['mods'] or config['users'][user]['admin']:
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
        if not config['users'][channel]['speedrun']: return
        try:
            cat = "x"
            category = "y"
            x = [0,0]
            if len(message.split(' ')) == 1: game = api.getTwitchData(channel)['game']
            else: game = message.split(' ')[1]
            data = api.getSRCNAData(game,"wr","")
            if data['data'] == []: data = api.getSRCNFData(game, "wr","")
            game = data['data'][0]['names']['international']
            categoryData = api.getSRCNCategories(data['data'][0]['links'][4]['uri'])
            if len(message.split(' ')) <= 2:
                twitchData = api.getTwitchData(channel)
                for cat in categoryData['data']:
                    if cat['name'].lower() in twitchData['status'].lower():
                        category = cat['name']
                        cat = category
                        break
                if category != cat:
                    link = data['data'][0]['links'][8]['uri'] + "?embed=category,players&top=1"
                else:
                    link = data['data'][0]['links'][4]['uri']
                    cData = api.getSRCNCategories(link)
                    for c in cData['data']:
                        if c['type'] == "per-game" and c['name'].lower() == category.lower(): link = c['links'][5]['uri'] + "?embed=category,players&top=1"
            else:
                category = message.split(' ',2)[2]
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
            if wrTime == 0 and float(x[0]) == 0:
                bot.say(channel, "The specified category doesn't exist")
            elif wrTime != 0 and float(x[0]) == 0:
                bot.say(channel, "The world record in {} {} is {} by {} | Run Page: {}".format(game.encode('utf8'), category, timeString, runner, page))
            elif float(x[0]) != 0:
                wrDec = str(x[0])
                bot.say(channel, "The world record in {} {} is {}{} by {} | Run Page: {}".format(game.encode('utf8'), category, timeString, wrDec[1:], runner, page))
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
            srldata = api.getSRLData()
            for x in xrange(0,len(srldata['races'])):
                srlracers = []
                for k,v in srldata['races'][x]['entrants'].iteritems():
                    if splitmessage[1] == 'srl' and fracer in srldata['races'][x]['entrants'][k]['twitch']:
                        bot.say(channel, 'http://www.speedrunslive.com/race/?id={}'.format(srldata['races'][x]['id']))
                        return
                    if len(srldata['races'][x]['entrants'][k]['twitch']) != 0:
                        twitchData = api.getTwitchData(srldata['races'][x]['entrants'][k]['twitch'].lower())
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
        data = api.getYouTubeData(video_id)
        title = data['items'][0]['snippet']['title']
        videoPoster = data['items'][0]['snippet']['channelTitle']
        if user in config['usernicks']: user = config['usernicks'][user]
        bot.say(channel,'{} linked: {} by {}'.format(user, title.encode('utf8'), videoPoster.encode('utf8')))

    def executeSet(self, bot, user, channel, message):
        if user == channel or config['users'][user]['admin']:
            if message.split(' ')[1] == 'trigger': config['users'][channel]['trigger'] = message.split(' ')[2].strip()
            if message.split(' ')[2] == 'admin' and user == 'powderedmilk_':
                config['users'][message.split(' ')[1]]['admin'] = True
                bot.say(channel,"{} set as bot admin".format(message.split(' ')[1]))
            config.save()

    def executeDogs(self, bot, user, channel, message):
        if not config['users'][channel]['dogs']: return
        bot.say(channel, ' '.join(config['dogs']))

    def executeSlots(self, bot, user, channel, message):
        if not config['users'][channel]['dogs']: return
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
        config.updateModList(channel)
        if user != channel and user not in config['users'][channel]['mods'] and not config['users'][user]['admin']: return
        if message.split(' ')[1] == 'emote':
            emotes = message.split(' ')[2:]
            for emote in emotes: config['users'][channel]['custom']['emotes'][emote] = 0
            bot.say(channel, '{} added to emote list'.format(' '.join(emotes)))
        elif message.split(' ')[1] == 'command':
            command = message.split(' ')[2]
            response = message.split(' ',3)[3]
            config['users'][channel]['custom']['commands'][command] = response
            bot.say(channel, '{} added to this channel\'s custom commands.'.format(command))
        elif message.split(' ')[1] == 'quote' and config['users'][channel]['quote']:
            qid = str(len(config['users'][channel]['quotes'].keys()) + 1)
            quote = message.split(' ',2)[2]
            config['users'][channel]['quotes'][qid] = quote
            bot.say(channel,"{} added to the this channels quote list with the id:{}".format(quote,qid))
        elif message.split(' ')[1] == 'faq' and (user == channel or config['users'][user]['admin']):
            game = api.getTwitchData(channel)['game']
            faq = message.split(' ',2)[2]
            config['users'][channel]['faq'][game] = faq
            bot.say(channel,"{}'s FAQ set to {}".format(game,faq))
        elif message.split(' ')[1] == 'global' and config['users'][user]['admin']:
            command = message.split(' ')[3].lower()
            cuser = message.split(' ')[2]
            response = message.split(' ',4)[4]
            config['users'][cuser]['pcommands'][command] = response
            print config['users'][cuser]['pcommands'].keys()
            bot.say(channel, "{} can now use {}!".format(cuser,command))
        config.save()
        return


    def executeDelCustom(self, bot, user, channel, message):
            config.updateModList(channel)
            if user != channel and user not in config['users'][channel]['mods'] and not config['users'][user]['admin']: return
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
            config.save()
            return

    def randomQuote(self, bot, user, channel, message):
        if not config['users'][channel]['quote']: return
        if len(message.split(' ')) == 1: qid = random.choice(config['users'][channel]['quotes'].keys())
        elif len(message.split(' ')) == 2: qid = message.split(' ')[1]
        bot.say(channel, "{} - id: {}".format(config['users'][channel]['quotes'][qid],qid))

    def executeMultitwitch(self, bot, user, channel, message):
        if not config['users'][channel]['multi']: return
        mchannels = message.split(' ')[2:]
        multi = message.split(' ')[1]
        if multi not in config['multitwitch'].keys(): bot.say(channel, 'I don\'t know {}, choose from {}'.format(multi,','.join(config['multitwitch'].keys())))
        if channel not in mchannels: mchannels.append(channel)
        bot.say(channel, '{}{}'.format(config['multitwitch'][multi],'/'.join(set(mchannels))))

    def executeNick(self, bot, user, channel, message):
        config['usernicks'][user] = message.split(' ',1)[1]
        bot.say(channel,"{}'s nick set to {}.".format(user,config['usernicks'][user]))
        config.save()

    def customFAQ(self, bot, user, channel, message):
        if not config['users'][channel]['utility']: return
        game = api.getTwitchData(channel)['game']
        if game in config['users'][channel]['faq'].keys(): bot.say(channel,"The FAQ for {} is {}.".format(game,config['users'][channel]['faq'][game]))
        else: bot.say(channel,"{} doesn't have a set FAQ in this channel, type {}new faq FAQ-link to set it for this game.".format(game, config['users'][channel]['trigger']))

    def executeCommands(self, bot, user, channel, message):
        #Fucking clean this up, please, for the love of god.
        config.updateModList(channel)
        commandL = []
        if user in config['users'].keys():
            if user == channel or config['users'][user]['admin']: commandL.extend(["{}help".format(config['users'][channel]['trigger']),"{}about".format(config['users'][channel]['trigger'])])
        if config['users'][channel]['dogs']: commandL.extend(["{}dogs".format(config['users'][channel]['trigger']),"{}slots".format(config['users'][channel]['trigger'])])
        if config['users'][channel]['dogfacts']: commandL.append("{}dogfacts".format(config['users'][channel]['trigger']))
        if config['users'][channel]['multi']: commandL.append("{}multi".format(config['users'][channel]['trigger']))
        if config['users'][channel]['speedrun']: commandL.extend(["{}wr".format(config['users'][channel]['trigger']),"{}pb".format(config['users'][channel]['trigger'])])
        if config['users'][channel]['utility']: commandL.extend(["{}uptime".format(config['users'][channel]['trigger']),"{}hl".format(config['users'][channel]['trigger']),"{}dhl".format(config['users'][channel]['trigger']),"{}highlights".format(config['users'][channel]['trigger']),"{}faq".format(config['users'][channel]['trigger'])])
        if config['users'][channel]['quote']: commandL.append("{}quote".format(config['users'][channel]['trigger']))
        for command in config['users'][channel]['custom']['commands'].keys(): commandL.append(command)
        if user in config['users'][channel]['mods'] or user == channel: commandL.extend(["{}add".format(config['users'][channel]['trigger']),"{}disable".format(config['users'][channel]['trigger']),"{}modules".format(config['users'][channel]['trigger'])])
        elif user in config['users'].keys() and config['users'][user]['admin']:commandL.extend(["{}add".format(config['users'][channel]['trigger']),"{}disable".format(config['users'][channel]['trigger']),"{}modules".format(config['users'][channel]['trigger'])])
        if user in config['users'].keys() and (user == channel or config['users'][user]['admin']): commandL.append("{}part".format(config['users'][channel]['trigger']))
        if user in config['users'].keys(): commandL.extend(config['users'][user]['pcommands'].keys())
        bot.say(channel,"Your available commands in this channel are: {}".format(', '.join(commandL)))

    def executeModules(self, bot, user, channel, message):
        bot.say(channel,"Available modules are: dogs, dogfacts, multi, youtube, speedrun, utility, and quote.")

    def executeHelp(self, bot, user, channel, message):
        if user != channel and channel != config['nickname'] and not config['users'][user]['admin']: return
        parts = message.split(' ')
        if len(parts) == 2 and config['users'][channel]['trigger'] in parts[1]: parts[1] = parts[1][1:]
        if len(parts) == 1: bot.say(channel,"This command is used to explain commands, for an explanation of a command do {}help <command> (without the brackets). Example: {}help commands".format(config['users'][channel]['trigger'],config['users'][channel]['trigger'],config['users'][channel]['trigger'],config['users'][channel]['trigger']))
        elif len(parts) == 2 and parts[1] in config['commands'].keys(): bot.say(channel,config['commands'][parts[1]].format(config['users'][channel]['trigger']))
        elif len(parts) == 2 and parts[1] in config['users'][channel]['custom']['commands'].keys() or "{}{}".format(config['users'][channel]['trigger'],parts[1]) in config['users'][channel]['custom']['commands'].keys(): bot.say(channel, "This is a custom command in this channel, to delete it type {}del command command-name".format(config['users'][channel]['trigger']))
        else: bot.say(channel, "That command isn't available or doesn't have a description, type {}commands to see available commands.".format(config['users'][channel]['trigger']))
        print "{}{}".format(config['users'][channel]['trigger'],parts[1])

    def executeAbout(self, bot, user, channel, message):
        bot.say(channel, "I'm a bot made by powderedmilk_ or something, use {}help for more info. [Bot Last Updated: August 6th, 2015]".format(config['users'][channel]['trigger']))

    def executeUptime(self, bot, user, channel, message):
        if not config['users'][channel]['utility']: return
        l = api.getLiveSince(bot, user, channel)
        if l is not 0: bot.say(channel, "{} has been live for {}".format(channel,str(l)[:-7]))
        else: bot.say(channel,"{} is not currently live".format(channel))

    def addHighlight(self, bot, user, channel, message):
        config.updateModList(channel)
        if user == channel or user in config['users'][channel]['mods'] or config['users'][user]['admin']:
            api.liveSince = str(api.getLiveSince(bot,user,channel))[:-7]
            if liveSince is not "0" and len(message.split(' ',1)) == 2:
                config['users'][channel]['highlights'].append(liveSince + ' "{}"'.format(message.split(' ',1)[1]))
                bot.say(channel,"{} added to highlight list".format(liveSince))
                config.save()
            elif liveSince is not "0" and len(message.split(' ',1)) == 1:
                config['users'][channel]['highlights'].append(liveSince)
                bot.say(channel,"{} added to highlight list".format(liveSince))
                config.save()

    def returnHighlights(self, bot, user, channel, message):
        if user != channel and not config['users'][user]['admin']: return
        bot.say(channel,"The timestamps for the highlights of your last broadcast are {}".format(', '.join(config['users'][channel]['highlights'])))

    def delHighlights(self, bot, user, channel, message):
        if user != channel and not config['users'][user]['admin']: return
        config['users'][channel]['highlights'] = []
        bot.say(channel,"Highlight timestamps deleted.")
        config.save()

    def executeUserBase(self, bot, user, channel, message):
        if config['users'][user]['admin']: bot.say(channel,str(len(config['users'].keys())))

    def getAdmins(self, bot, user, channel, message):
        if not user == channel and not config['users'][user]['admin']: return
        admins = []
        for user in config['users'].keys():
            if config['users'][user]['admin']: admins.append(user.title())
        bot.say(channel,"{}".format(', '.join(admins)))


    def start(self):
        reactor.callInThread(self.loop)

    def saveConfig(self, bot, user, channel, message):
        if config['users'][user]['admin']:
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
        ('{}add', 'executeAdd', True),
        ('{}disable', 'executeDisable', True),
        ('{}pb', 'executePb', True),
        ('{}wr', 'executeWr', True),
        ('{}splits','executeSplits', True),
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
        ('{}commands','executeCommands',True),
        ('+users','executeUserBase',False),
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
        ('{}quote', 'randomQuote', False)
    ]


WooferHandler = WooferBotCommandHandler()

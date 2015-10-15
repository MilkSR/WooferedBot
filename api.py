import json
import urllib
import handler
import datetime
import isodate
import pytz
from settings import config

def getTwitchData(channel):
    twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
    twitchResponse = urllib.urlopen(twitchUrl);
    return json.load(twitchResponse)

def getSRCData(game,f,runner):
    if f == "wr": url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8')
    elif f == "pb": url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8') + "&user=" + runner
    response = urllib.urlopen(url)
    return json.load(response)

def getSRCIDData(f, runner):
    if f == "pb": url = "http://www.speedrun.com/api/v1/users?{}".format(runner)
    response = urllib.urlopen(url)
    return json.load(response)

def getSRCUData(uid,game):
    url = "http://www.speedrun.com/api/v1/users/{}/personal-bests?embed=game,category&game={}".format(uid,game)
    response = urllib.urlopen(url)
    return json.load(response)

def getSRCNAData(game, f, runner):
    if f == "wr": url = "http://www.speedrun.com/api/v1/games?abbreviation={}".format(game)
    response = urllib.urlopen(url)
    return json.load(response)

def getSRCNFData(game, f, runner):
    if f == "wr": url = "http://www.speedrun.com/api/v1/games?name={}".format(game)
    response = urllib.urlopen(url)
    return json.load(response)

def getSRCRun(rid):
    url = "http://www.speedrun.com/api/v1/runs/{}?embed=category,players,game,level".format(rid)
    response = urllib.urlopen(url)
    return json.load(response)


def getSRCNCategories(category):
    response = urllib.urlopen(category)
    return json.load(response)

def getSRCNLeaderboard(link):
    response = urllib.urlopen(link)
    return json.load(response)

def getYouTubeData(video_id):
    url = "https://www.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&id={}&fields=items(id%2Csnippet(title%2CchannelTitle)%2CcontentDetails(duration)%2Cstatistics(viewCount%2ClikeCount%2CdislikeCount))&key={}".format(video_id, config["YTAuthKey"])
    response = urllib.urlopen(url)
    return json.load(response)

def getSRLData():
    srlurl = "http://api.speedrunslive.com/races"
    srlresponse = urllib.urlopen(srlurl);
    return json.load(srlresponse)

def getLiveSince(bot, user, channel):
    url = "https://api.twitch.tv/kraken/streams/" + channel
    response = urllib.urlopen(url)
    data = json.load(response)
    if data['stream'] is None: return 0
    startTime = data['stream']['created_at']
    a = isodate.parse_datetime(startTime)
    b = datetime.datetime.now(pytz.utc)
    liveSince = b - a
    return liveSince

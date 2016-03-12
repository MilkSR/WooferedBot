import json
import urllib
import handler
import datetime
import isodate
import pytz
import tweepy
import requests
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
    if f == "wr": url = "http://www.speedrun.com/api/v1/games?name={}&max=1".format(game)
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

def getButt(t,l,page):
    url = "http://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags={}+ass+-splatoon&limit={}&pid={}".format(t,l,page)
    response = urllib.urlopen(url)
    return json.load(response)
    
def getLastfmData(user):
    url = "https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={}&api_key=57ee3318536b23ee81d6b27e36997cde&format=json".format(user)
    response = urllib.urlopen(url)
    return json.load(response)

def getTwitterData(api,id):
    return api.get_status(id)._json
    
def getFFZEmoteData(id):
    url = "http://api.frankerfacez.com/v1/emote/{}".format(id)
    response = urllib.urlopen(url)
    return json.load(response)

def getPokedex():
    url = "http://www.pokeapi.co/api/v1/pokedex/1"
    response = requests.get(url)
    return response.json()

def getPokemon(apiEnd):
    url = "http://www.pokeapi.co/{}".format(apiEnd)
    response = requests.get(url)
    return response.json()
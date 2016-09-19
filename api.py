import json
import urllib
import handler
import datetime
import isodate
import pytz
import tweepy
import requests
import soundcloud
from settings import config

def getTwitchData(channel):
    twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
    twitchResponse = requests.get(twitchUrl, headers={'Client-ID': config['twitchCID']})
    return twitchResponse.json()

def getSRCData(game,f,runner):
    if f == "wr": url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8')
    elif f == "pb": url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8') + "&user=" + runner
    response = requests.get(url)
    return response.json()

def getSRCIDData(f, runner):
    if f == "pb": url = "http://www.speedrun.com/api/v1/users?{}".format(runner)
    response = requests.get(url)
    return response.json()

def getSRCUData(uid,game):
    url = "http://www.speedrun.com/api/v1/users/{}/personal-bests?embed=game,category&game={}".format(uid,game)
    response = requests.get(url)
    return response.json()

def getSRCNAData(game, f, runner):
    if f == "wr": url = "http://www.speedrun.com/api/v1/games?abbreviation={}".format(game)
    response = requests.get(url)
    return response.json()

def getSRCNFData(game, f, runner):
    if f == "wr": url = "http://www.speedrun.com/api/v1/games?name={}&max=1".format(game)
    response = requests.get(url)
    return response.json()

def getSRCRun(rid):
    url = "http://www.speedrun.com/api/v1/runs/{}?embed=category,players,game,level".format(rid)
    response = requests.get(url)
    return response.json()

def getSRCNCategories(category):
    response = requests.get(category)
    return response.json()

def getSRCNLeaderboard(link):
    response = requests.get(link)
    return response.json()

def getYouTubeData(video_id):
    url = "https://www.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&id={}&fields=items(id%2Csnippet(title%2CchannelTitle)%2CcontentDetails(duration)%2Cstatistics(viewCount%2ClikeCount%2CdislikeCount))&key={}".format(video_id, config["YTAuthKey"])
    response = urllib.urlopen(url)
    return json.load(response)

def getSRLData():
    srlurl = "http://api.speedrunslive.com/races"
    srlresponse = urllib.urlopen(srlurl);
    return json.load(srlresponse)

def getSCData(client,trackURL):
    return client.get('/resolve', url=trackURL)

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

def getButt(page):
    url = "https://danbooru.donmai.us/posts.json?tags=butt%20rating:safe&limit=100&page={}".format(page)
    response = requests.get(url)
    return response.json()
    
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

def getStrawpoll(pid):
    url = "https://strawpoll.me/api/v2/polls/{}".format(pid)
    response = requests.get(url)
    return response.json()

def getTwitchpoll(pid):
    url = "http://api.twitchpoll.com/v1/poll/{}".format(pid)
    response = requests.get(url)
    return response.json()
    
def getTwitchVod(vc, vid):
    url = "https://api.twitch.tv/kraken/videos/{}{}".format(vc, vid)
    response = requests.get(url, headers={'Client-ID': config['twitchCID']})
    return response.json()

def getTwitchClip(c,clip):
    url = "https://clips.twitch.tv/api/v1/clips/{}/{}".format(c, clip)
    response = requests.get(url, headers={'Client-ID': config['twitchCID']})
    return response.json()
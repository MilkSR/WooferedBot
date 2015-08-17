import json
import urllib
import handler
from settings import config

def getTwitchData(bot, user, channel):
    twitchUrl = "https://api.twitch.tv/kraken/channels/" + channel
    twitchResponse = urllib.urlopen(twitchUrl);
    return json.load(twitchResponse)

def getSRCData(bot, user, channel, game):
    url = "http://www.speedrun.com/api_records.php?game=" + game.encode('utf8')
    response = urllib.urlopen(url)
    return json.load(response)

def getYouTubeData(bot, user, channel, video_id):
    url = "https://www.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&id={}&fields=items(id%2Csnippet(title%2CchannelTitle)%2CcontentDetails(duration)%2Cstatistics(viewCount%2ClikeCount%2CdislikeCount))&key={}".format(video_id, config["YTAuthKey"])
    response = urllib.urlopen(url)
    return json.load(response)

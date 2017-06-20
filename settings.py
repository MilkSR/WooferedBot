import os
import json
import urllib

def byteify(input):
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


class WooferConfig(dict):
    cfg_file = 'wooferbot.config'
    cfg_backup = 'wooferbot.backup'

    def loadAll(self):
        try:
            with open(WooferConfig.cfg_file, "r+") as f:
                self.update(byteify(json.load(f)))
        except Exception as err:
            # Log the damn error.
            print "Problem loading config:", repr(err)
        self['users'] = {}
        for cfgFile in os.listdir("config"):
            if cfgFile.split('.')[1] == "cfg":
                with open("config/{}".format(cfgFile), "r+") as uCfg:
                    self['users'][cfgFile.split('.')[0]] = byteify(json.load(uCfg))
        config.sanitize()
        
    def load(self, channel):
        del self['users'][channel]
        with open("config/{}.cfg".format(channel), "r") as f:
            self['users'][channel] = byteify(json.load(f))

    def save(self, channel, **FnS):
        if 'san' not in FnS.keys(): config.sanitize()
        if 'file' in FnS.keys(): 
            file = FnS['file']
        else:
            file = WooferConfig.cfg_file
        if file == WooferConfig.cfg_file:
            if  channel != "all channels":
                file = "config/{}.cfg".format(channel)
        elif file == WooferConfig.cfg_backup:
            if channel != "all channels":
                file = "config/{}.bkup".format(channel)
        if file != WooferConfig.cfg_backup and file != WooferConfig.cfg_file:
            coppeh = self['users'][channel]
        else:
            coppeh = self.copy()
        if 'dogsc' in coppeh.keys(): del coppeh['dogsc']
        if 'ltcu' in coppeh.keys(): del coppeh['ltcu']
        if 'users' in coppeh.keys(): del coppeh['users']
        with open(file, 'w') as f:
            json.dump(coppeh, f, indent=4, sort_keys=True)
        if channel == "all channels" and file == WooferConfig.cfg_file:
                for user in self['users']:
                    with open("config/{}.cfg".format(user), "w+") as uCfg:
                        json.dump(self['users'][user], uCfg, indent=4, sort_keys=True)
        elif channel == "all channels" and file == WooferConfig.cfg_backup:
            for user in self['users']:
                with open("config/{}.bkup".format(user), "w+") as uCfg:
                    json.dump(self['users'][user], uCfg, indent=4, sort_keys=True) 

    def sanitize(self):
        config['channels'].sort()
        for c in config['channels']:
            if c not in config['users'].keys():
                config['users'][c] = {}
                config['users'][c]['status'] = "user"
        for c in config['users'].keys():
            if 'pcommands' not in config['users'][c].keys(): config['users'][c]['pcommands'] = {}
            if 'nick' not in config['users'][c].keys(): config['users'][c]['nick'] = None
            if config['users'][c]['status'] != "chatter":
                for i in ['dogfacts','multi','speedrun','linkinfo','utility','quote','faqm','lastfm','novelty','pokedex','butt','whisper']:
                    if i not in config['users'][c].keys(): config['users'][c][i] = False
                if 'dogs' not in config['users'][c].keys(): config['users'][c]['dogs'] = True
                if 'ignore' not in config['users'][c].keys(): config['users'][c]['ignore'] = []
                if 'custom' not in config['users'][c].keys():
                    config['users'][c]['custom'] = {}
                for x in ['commands','emotes','phrases','modCommands']:
                    if x not in config['users'][c]['custom'].keys():
                        config['users'][c]['custom'][x] = {}
                if 'list' not in config['users'][c]['custom']['emotes']: config['users'][c]['custom']['emotes']['list'] = []
                if 'trigger' not in config['users'][c].keys(): config['users'][c]['trigger'] = '+'
                if 'mods' not in config['users'][c].keys(): config['users'][c]['mods'] = []
                if 'highlights' not in config['users'][c].keys(): config['users'][c]['highlights'] = []
                if 'shadowbans' not in config['users'][c].keys(): config['users'][c]['shadowbans'] = []
                if 'faq' not in config['users'][c].keys(): config['users'][c]['faq'] = {}
                if 'quotes' not in config['users'][c].keys(): config['users'][c]['quotes'] = {}
                if 'count' not in config['users'][c]['quotes'].keys(): config['users'][c]['quotes']['count'] = len(config['users'][c]['quotes'].keys())
                if 'lastfma' not in config['users'][c].keys(): config['users'][c]['lastfma'] = ""
                if 'added by' not in config['users'][c].keys(): config['users'][c]['added by'] = "N/A"
                if 'time added' not in config['users'][c].keys(): config['users'][c]['time added'] = "N/A"
                if 'bannedwords' not in config['users'][c].keys(): config['users'][c]['bannedwords'] = {}
                if 'count' in config['users'][c]['quotes'].keys(): del config['users'][c]['quotes']['count']
                if 'mods' in config['users'][c].keys(): del config['users'][c]['mods']
                if 'emoteposting' not in config['users'][c].keys():
                    if config['users'][c]['dogs']: config['users'][c]['emoteposting'] = True
                    else: config['users'][c]['emoteposting'] = False
            if config['users'][c]['status'] == "chatter" and (len(config['users'][c]['pcommands'].keys()) == 0 and config['users'][c]['nick'] == None): 
                del config['users'][c]

        # init dogcount dicts
        dogsc = self.setdefault('dogsc',{})
        if 'dogCount' not in dogsc: dogsc['dogCount'] = {}
        for c in self['users'].keys():
            if c not in dogsc['dogCount']:
                dogsc['dogCount'][c] = 0
        ltcu = self.setdefault('ltcu',{})
        if 'commands' not in ltcu: ltcu['commands'] = {}
        for c in self['users'].keys():
            if c not in ltcu['commands']: ltcu['commands'][c] = {}
            for co in self['commands'].keys():
                if co not in ltcu['commands'][c].keys():
                    ltcu['commands'][c][co] = 0
        
        #save backup of config
        config.save("all channels", san = 0, file = WooferConfig.cfg_backup)

    def checkConfig(channel, mod):
        if config['users'][channel][mod]:
            return true
        if not config['users'][channel][mod]:
            return false

    def defaults(self):
        # defaults
        self['nickname'] = '???'
        self['password'] = 'oauth:???????'
        self['dogs'] = ["FrankerZ", "ZreknarF", "LilZ", "ZliL", "RalpherZ", "ZrehplaR"]


config = WooferConfig()

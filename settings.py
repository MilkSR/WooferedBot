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

    def load(self):
        try:
            with open(WooferConfig.cfg_file) as f:
                self.update(byteify(json.load(f)))
        except Exception as err:
            # Log the damn error.
            print "Problem loading config:", repr(err)

            # try to save original file under different filename
            import os.path, os, time
            try:
                if os.path.isfile(WooferConfig.cfg_file):
                    parts = WooferConfig.cfg_file.split('.')
                    backup_name = '{0}_{2}.{1}'.format(''.join(parts[0:-1]), parts[-1], time.strftime("%Y%m%d-%H%M%S"))
                    os.rename(WooferConfig.cfg_file, backup_name)
            except:
                pass
            config.defaults()

        config.sanitize()

    def save(self):
        config.sanitize()
        coppeh = self.copy()
        del coppeh['dogsc']
        del coppeh['ltcu']
        with open(WooferConfig.cfg_file, 'w') as f:
            json.dump(coppeh, f, indent=4, sort_keys=True)

    def sanitize(self):
        for c in config['channels']:
            if c not in config['users'].keys():
                config['users'][c] = {}
                config['users'][c]['status'] = "user"
        for c in config['users'].keys():
            if 'pcommands' not in config['users'][c].keys(): config['users'][c]['pcommands'] = {}
            if config['users'][c]['status'] != "chatter":
                for i in ['dogfacts','multi','speedrun','linkinfo','utility','quote','faqm','lastfm','butts','novelty','pokedex','butt']:
                    if i not in config['users'][c].keys(): config['users'][c][i] = False
                if 'dogs' not in config['users'][c].keys(): config['users'][c]['dogs'] = True
                if 'ignore' not in config['users'][c].keys(): config['users'][c]['ignore'] = []
                if 'custom' not in config['users'][c].keys():
                    config['users'][c]['custom'] = {}
                for x in ['commands','emotes','phrases']:
                    if x not in config['users'][c]['custom'].keys():
                        config['users'][c]['custom'][x] = {}
                if 'trigger' not in config['users'][c].keys(): config['users'][c]['trigger'] = '+'
                if 'mods' not in config['users'][c].keys(): config['users'][c]['mods'] = []
                if 'highlights' not in config['users'][c].keys(): config['users'][c]['highlights'] = []
                if 'faq' not in config['users'][c].keys(): config['users'][c]['faq'] = {}
                if 'quotes' not in config['users'][c].keys(): config['users'][c]['quotes'] = {}
                if 'count' not in config['users'][c]['quotes'].keys(): config['users'][c]['quotes']['count'] = len(config['users'][c]['quotes'].keys())
                if 'lastfma' not in config['users'][c].keys(): config['users'][c]['lastfma'] = ""
                if 'added by' not in config['users'][c].keys(): config['users'][c]['added by'] = "N/A"
                if 'time added' not in config['users'][c].keys(): config['users'][c]['time added'] = "N/A"
                if 'cooldowns' not in config['users'][c].keys() or type(config['users'][c]['cooldowns']) == "list": config['users'][c]['cooldowns'] = {}
                for co in config['commands'].keys():
                    if co not in config['users'][c]['cooldowns'].keys(): config['users'][c]['cooldowns'][co] = 1
                if 'mods' in config['users'][c].keys(): del config['users'][c]['mods']
            if config['users'][c]['status'] == "chatter" and len(config['users'][c]['pcommands'].keys()) == 0: 
                del config['users'][c]

        # init dogcount dicts
        dogsc = self.setdefault('dogsc',{})
        if 'dogCount' not in dogsc: dogsc['dogCount'] = {}
        for c in self['users'].keys():
            if c not in dogsc['dogCount']:
                dogsc['dogCount'][c] = {}
            for d in self['dogs']:
                if d not in dogsc['dogCount'][c]:
                    dogsc['dogCount'][c][d] = 0
        ltcu = self.setdefault('ltcu',{})
        if 'commands' not in ltcu: ltcu['commands'] = {}
        for c in self['users'].keys():
            if c not in ltcu['commands']: ltcu['commands'][c] = {}
            for co in self['commands'].keys():
                if co not in ltcu['commands'][c].keys():
                    ltcu['commands'][c][co] = 0

    def defaults(self):
        # defaults
        self['nickname'] = '???'
        self['password'] = 'oauth:???????'
        self['dogs'] = ["FrankerZ", "ZreknarF", "LilZ", "ZliL", "RalpherZ", "ZrehplaR"]


config = WooferConfig()

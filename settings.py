import json

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
        # remove leftovers/duplicates
        self['channels'] = list(set(self['channels'])) # remove dupes
        self['channels'].sort()
        for s in ['speedrunchannels', 'kadgarchannels', 'dogfactschannels']:
            self[s] = list(set(self['channels']) & set(self[s])) # remove invalid shit
            self[s].sort()

        with open(WooferConfig.cfg_file, 'w') as f:
            json.dump(self, f, indent=4, sort_keys=True)

    def sanitize(self):
        for key in ['dogs', 'channels', 'admin_channels', 'dogfactschannels', 'kadgarchannels', 'speedrunchannels']:
            if key not in self: self[key] = []

        # init dogcount dicts
        if 'dogCount' not in self: self['dogCount'] = {}
        for c in self['channels']:
            if c not in self['dogCount']:
                self['dogCount'][c] = {}
            for d in self['dogs']:
                if d not in self['dogCount'][c]:
                    self['dogCount'][c][d] = 0


    def defaults(self):
        # defaults
        self['nickname'] = '???'
        self['password'] = 'oauth:???????'
        self['dogs'] = ["FrankerZ", "ZreknarF", "LilZ", "ZliL", "RalpherZ", "ZrehplaR"]
        self['admin_channels'] = [self['nickname']]


config = WooferConfig()
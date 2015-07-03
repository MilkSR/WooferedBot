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
        for user in config['users'].keys():
            if user not in config['channels']: config['channels'].append(user)
        for channel in config['channels']:
            if channel not in config['users'].keys(): config['channels'].remove(channel)
        coppeh = self.copy()
        del coppeh['dogsc']
        with open(WooferConfig.cfg_file, 'w') as f:
            json.dump(coppeh, f, indent=4, sort_keys=True)

    def sanitize(self):
        # init dogcount dicts
        dogsc = self.setdefault('dogsc',{})
        if 'dogCount' not in dogsc: dogsc['dogCount'] = {}
        for c in self['users'].keys():
            if c not in dogsc['dogCount']:
                dogsc['dogCount'][c] = {}
            for d in self['dogs']:
                if d not in dogsc['dogCount'][c]:
                    dogsc['dogCount'][c][d] = 0


    def defaults(self):
        # defaults
        self['nickname'] = '???'
        self['password'] = 'oauth:???????'
        self['dogs'] = ["FrankerZ", "ZreknarF", "LilZ", "ZliL", "RalpherZ", "ZrehplaR"]


config = WooferConfig()
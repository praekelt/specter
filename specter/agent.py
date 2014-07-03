from specter import version

class Agent(object):
    def __init__(self, config):
        self.config = config

    def get_version(self, request):
        return {"specter": version.VERSION}

    get_ = get_version

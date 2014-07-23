import yaml

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.web import server
from twisted.internet import ssl

from zope.interface import implements

from specter import service


class Options(usage.Options):
    optParameters = [
        ["port", "p", 2400, "The port to listen on"],
        ["config", "c", "specter.yml", "Config file"],
    ]

class SpecterServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "specter"
    description = "A simple server agent"
    options = Options
    def makeService(self, options):
        config = yaml.load(open(options['config']))
        
        return internet.SSLServer(
            int(options['port']),
            server.Site(service.SiteRoot(config)),
            ssl.DefaultOpenSSLContextFactory(
                config['ssl-key'],
                config['ssl-cert']
            )
        )

serviceMaker = SpecterServiceMaker()

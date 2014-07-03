from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.web import server
from twisted.internet import ssl

import specter


class Options(usage.Options):
    optParameters = [
        ["port", "p", 2400, "The port to listen on"],
        ["config", "c", "specter.yml", "Config file"],
        ["key", None, "specter.key", "SSL key file"],
        ["cert", None, "specter.crt", "SSL certificate file"]
    ]

class SpecterServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "specter"
    description = "Distributex - A simple mutex lock service"
    options = Options
    def makeService(self, options):
        return internet.SSLServer(
            int(options['port']),
            server.Site(specter.SiteRoot(options['config'])),
            ssl.DefaultOpenSSLContextFactory(
                options['key'],
                options['cert']
            )
        )

serviceMaker = SpecterServiceMaker()

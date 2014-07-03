# -*- coding: utf-8 -*-
from twisted.application import internet, service
from twisted.web import server, resource, client
from twisted.internet import defer, reactor, threads, utils, task
from zope import interface

import json
import yaml
import time
import cgi
import random
import hmac
import hashlib
import base64

from specter import version, agent

class SiteRoot(resource.Resource):
    isLeaf = True
    addSlash = True

    def __init__(self, config):
        self.config = yaml.load(open(config))

        self.agent = agent.Agent(self.config)

        reactor.callWhenRunning(self.setup)

    def setup(self):
        pass

    def completeCall(self, response, request):
        # Render the json response from call
        response = json.dumps(response)
        request.write(response)
        request.finish()

    def jsonRequest(self, call, request, data=None):
        try:
            if data:
                m = '_'.join(call)
                return getattr(self.agent, 'post_'+m)(request, data)
            else:
                m = '_'.join(call)
                return getattr(self.agent, 'get_'+m)(request)
        except AttributeError:
            return {"error": "Invalid call %s" % m}

    def getHeader(self, request, header, default=None):
        head = request.requestHeaders.getRawHeaders(header)
        if head:
            return head[0]
        else:
            return default

    def getSecret(self, auth):
        # Just some test secret
        secrets = {'ahh3io45123hrqabf': '412YUDASdaqw123'}

        return secrets[auth]

    def checkSignature(self, request, data=None):
        auth = self.getHeader(request, 'authorization', None)
        sig = self.getHeader(request, 'sig', None)

        if not (auth and sig):
            return False

        sign = [auth, request.method, request.path]
        if data:
            sign.append(
                hashlib.sha1(data).hexdigest()
            )

        mysig = hmac.new(
            key = self.getSecret(auth),
            msg = '\n'.join(sign),
            digestmod = hashlib.sha1
        ).digest()

        return base64.b64encode(mysig) == sig


    def render_GET(self, request):
        if not self.checkSignature(request):
            return "Not authorized"

        request.setHeader("content-type", "application/json")
        # Get request
        call = request.path.strip('/').split('/')

        d = defer.maybeDeferred(self.jsonRequest, call, request)

        d.addCallback(self.completeCall, request)

        return server.NOT_DONE_YET

    def render_POST(self, request):
        request.setHeader("content-type", "application/json")
        # Get request
        call = request.path.strip('/').split('/')

        data = cgi.escape(request.content.read())

        if not self.checkSignature(request, data):
            return "Not authorized"

        d = defer.maybeDeferred(self.jsonRequest, call, request, 
            json.loads(data)
        )

        d.addCallback(self.completeCall, request)

        return server.NOT_DONE_YET


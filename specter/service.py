# -*- coding: utf-8 -*-
from twisted.web import server, resource
from twisted.internet import defer, reactor, task

import json
import cgi
import hmac
import hashlib
import base64
import socket

try:
    from urllib.parse import urlparse
except:
    from urlparse import urlparse

from specter import version, agent, client

class SiteRoot(resource.Resource):
    isLeaf = True
    addSlash = True

    def __init__(self, config):
        self.config = config

        self.agent = agent.Agent(self.config)
        self.client = client.SpecterClient(
            'localhost', config['authcode'], config['secret'])

        if config.get('webhook'):
            reactor.callWhenRunning(self.setup)

    @defer.inlineCallbacks
    def updateWebhook(self):
        """
        Updates the webhook, called by LoopingCall
        """
        url = self.config['webhook']
        path = urlparse(url).path

        data = json.dumps({
            'specter': version.VERSION,
            'hostname': socket.gethostbyaddr(socket.gethostname())[0]
        })
        
        try:
            request = yield self.client.httpsRequest(
                url,
                headers=self.client.signHeaders(path.lstrip('/'), data),
                method='POST',
                data=data
            )
            print "Updated webhook: %s" % url
        except Exception, e:
            print "Webhook failed: %s" % e

        defer.returnValue(None)

    def setup(self):
        self.update = task.LoopingCall(self.updateWebhook)

        self.update.start(
            int(self.config.get('update_time', 300))
        )

    def completeCall(self, response, request):
        # Render the json response from call
        response = json.dumps(response)
        request.write(response)
        request.finish()

    def jsonRequest(self, call, request, data=None):
        if data:
            m = 'post_'
        else:
            m = 'get_'

        method = m + '_'.join(call)

        try:
            if method in self.agent.methods:
                if data:
                    return getattr(self.agent, method)(request, data)
                else:
                    return getattr(self.agent, method)(request)
            else:
                for i in range(1, len(call)):
                    method = m + '_'.join(call[:-1*i])
                    if method in self.agent.methods:
                        args = call[-1*i:]
                        if data:
                            return getattr(self.agent, method)(request, args, data)
                        else:
                            return getattr(self.agent, method)(request, args)

        except Exception, e:
            return {"error": "Invalid call %s" % m}

    def getHeader(self, request, header, default=None):
        head = request.requestHeaders.getRawHeaders(header)
        if head:
            return head[0]
        else:
            return default

    def getSecret(self, auth):
        if auth == self.config['authcode']:
            return self.config['secret']

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


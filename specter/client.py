# -*- coding: utf-8 -*-
# Specter client library

import hashlib
import base64
import hmac
import urllib
import json

from zope.interface import implements

from twisted.web.iweb import IBodyProducer
from twisted.web.client import Agent, readBody
from twisted.internet import reactor, defer
from twisted.internet.ssl import ClientContextFactory
from twisted.web.http_headers import Headers

class WebClientContextFactory(ClientContextFactory):
    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)

class StringProducer(object):
    """
    Body producer for t.w.c.Agent
    """
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class SpecterClient(object):
    def __init__(self, host, auth, key, port=2400):
        self.host = host
        self.port = port
        self.auth = auth
        self.key = key

    def createSignature(self, path, data=None):
        if data:
            method = 'POST'
        else:
            method = 'GET'
        sign = [self.auth, method, '/' + path]
        if data:
            sign.append(
                hashlib.sha1(data).hexdigest()
            )

        mysig = hmac.new(key=self.key, msg='\n'.join(sign),
            digestmod=hashlib.sha1).digest()

        return base64.b64encode(mysig)

    @defer.inlineCallbacks
    def httpsRequest(self, path, headers={}, method='GET', data=None):
        url = 'https://%s:%s/%s' % (self.host, self.port, path)

        agent = Agent(reactor, WebClientContextFactory())

        if data:
            data = StringProducer(data)
        
        request = yield agent.request(
            method,
            url,
            Headers(headers),
            data
        )

        body = yield readBody(request)

        defer.returnValue(json.loads(body))

    def getRequest(self, path):
        sig = self.createSignature(path)

        headers = {
            'authorization': [self.auth],
            'sig': [sig]
        }

        return self.httpsRequest(path, headers=headers)

    def postRequest(self, path, data):
        sig = self.createSignature(path, data)

        headers = {
            'authorization': [self.auth],
            'sig': [sig]
        }

        return self.httpsRequest(
            path, headers=headers, method='POST', data=data)

    def __getattr__(self, method):

        if method[:4] == 'get_':
            path = '/'.join(method[4:].split('_'))
            return lambda: self.getRequest(path)

        elif method[:5] == 'post_':
            path = '/'.join(method[5:].split('_'))
            return lambda data: self.postRequest(path, data)

        else:
            raise AttributeError

from twisted.trial import unittest

from specter import service, client

class WhateverObject(object):
    def __init__(self, **kw):
        for k,v in kw.items():
            setattr(self, k, v)

def fakeRequest(path, method, headers):
    def getRawHeaders(x):
        if x in headers:
            return [headers[x]]
        else:
            return []

    return WhateverObject(
        method=method, 
        path=path,
        requestHeaders=WhateverObject(
            getRawHeaders=getRawHeaders
        )
    )

class Service(unittest.TestCase):
    def setUp(self):
        self.root = service.SiteRoot({'authcode': '123', 'secret': '456'})
        self.client = client.SpecterClient('localhost', '123', '456')

    def test_hmac(self):
        sig = self.client.createSignature('test')

        request = fakeRequest('/test', 'GET',
            {'sig': sig, 'authorization': '123'})

        val = self.root.checkSignature(request)
        self.assertEquals(val, True)


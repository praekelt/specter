import os

from twisted.internet import defer, utils

from specter import version

class Agent(object):
    def __init__(self, config):
        self.config = config
        self.methods = [m for m in dir(self) if m.startswith('post_') or m.startswith('get_')]

    def runShell(self, command):
        return utils.getProcessOutputAndValue(
            '/bin/sh', args=('-c', command)
        )

    def get_version(self, request):
        return {"specter": version.VERSION}

    get_ = get_version

    @defer.inlineCallbacks
    def get_databases(self, request):
        """
        Get any postgres databases
        """
        if os.path.exists('/var/lib/postgresql'):
            dbs, errors, code = yield self.runShell(
                'psql -At -U postgres -h localhost postgres -c "select datname,datcollate from pg_database"')

            db = []
            for l in dbs.strip('\n').split('\n'):
                if l.startswith('template') or l.startswith('postgres'):
                    continue
                db.append(l.split('|'))
        else:
            db = []

        defer.returnValue({'databases': db})

    @defer.inlineCallbacks
    def get_package(self , request, args):
        """
        Get package version and installation status
        """
        package = args[0]
        pkg, errors, code = yield self.runShell(
            'dpkg -s %s' % package
        )
        fields = {}
        if code == 0:
            for l in pkg.strip('\n').split('\n'):
                if l[0]==' ':
                    continue
                field = l.split(': ')[0]
                if field in ['Version', 'Status', 'Installed-Size']:
                    fields[field.lower()] = l.split(': ')[-1]

        defer.returnValue(fields)

    @defer.inlineCallbacks
    def post_install(self, request, data):
        """
        Install a package from a url or apt repo
        """
        if 'url' in data:
            url = data['url']
            fn = url.split('/')[-1]
            # Download the file
            inst, errors, code = yield utils.getProcessOutputAndValue(
                '/usr/bin/wget', args=('-c', '-O', '/tmp/'+fn, url))
            if code!=0:
                defer.returnValue({'error', inst+errors})
            else:
                # Installl with gdebi
                inst, errors, code = yield utils.getProcessOutputAndValue(
                    '/usr/bin/gdebi', args=('-n', '/tmp/'+fn))

            os.unlink('/tmp/'+fn)
        else:
            # Update apt
            r = yield self.runShell('apt-get update')
            # Install with apt
            inst, errors, code = yield utils.getProcessOutputAndValue(
                '/usr/bin/apt-get', args=('-q', '-y', '-o', 'DPkg::Options::=--force-confold', 'install', data['package']))

        defer.returnValue({
            'stdout': inst,
            'stderr': errors,
            'code': code
        })

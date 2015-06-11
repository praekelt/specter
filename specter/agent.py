import os

from twisted.internet import defer, utils, task, reactor
from twisted.python import log

import fcntl

from specter import version

class Agent(object):
    def __init__(self, config):
        self.config = config

        if os.path.exists('/etc/redhat-release'):
            self.os = 'Redhat'
        else:
            self.os = 'Ubuntu'

        self.methods = [m for m in dir(self) if m.startswith('post_') or m.startswith('get_')]

    @defer.inlineCallbacks
    def runShell(self, command):
        out, err, code = yield utils.getProcessOutputAndValue(
            '/bin/sh', args=('-c', command), env=os.environ
        )

        defer.returnValue((out+err, code))

    def get_version(self, request):
        return {"specter": version.VERSION}

    get_ = get_version

    @defer.inlineCallbacks
    def get_databases(self, request):
        """
        Get any postgres databases
        """
        log.msg('Postgres databases requested from %s' % request.getClientIP())

        if os.path.exists('/var/lib/postgresql'):
            dbs, code = yield self.runShell(
                'psql -At -U postgres -h localhost postgres -c "select datname,datcollate from pg_database"')

            db = []
            if code == 0:
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
        log.msg('Package details for %s requested from %s' % (package, request.getClientIP()))
        pkg, code = yield self.runShell(
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

    def checkDpkgLock(self):
        if not os.path.exists('/var/lib/dpkg/lock'):
            return False

        with open('/var/lib/dpkg/lock', 'w') as handle:
            try:
                fcntl.lockf(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return False
            except IOError:
                return True

    @defer.inlineCallbacks
    def waitDpkg(self):
        if self.checkDpkgLock():
            log.msg('Waiting for dpkg lock...')
            while self.checkDpkgLock():
                yield task.deferLater(reactor, 1, lambda: None)

    @defer.inlineCallbacks
    def _ubuntu_install(self, request, data):
        """
        Install a package from a url or apt repo
        Accepts: {'package': str, ['url': str]}
        """
        if 'url' in data:
            url = data['url']
            log.msg('Package instalation %s requested from %s' % (
                url, request.getClientIP()))
            fn = url.split('/')[-1]
            # Download the file
            inst, errors, code = yield utils.getProcessOutputAndValue(
                '/usr/bin/wget', args=('-nv', '-c', '-O', '/tmp/'+fn, url))

            yield self.waitDpkg()

            if code!=0:
                defer.returnValue({'error': inst+errors})
            else:
                # Install with gdebi (needs a full shell)
                inst, errors, code = yield utils.getProcessOutputAndValue(
                    '/usr/bin/gdebi', args=('-nq', '/tmp/'+fn), env=os.environ
                )
                os.unlink('/tmp/'+fn)
        else:
            log.msg('Package instalation %s requested from %s' % (
                data['package'], request.getClientIP()))
            # Update apt
            yield self.waitDpkg()
            r = yield self.runShell('apt-get update')
            # Install with apt
            yield self.waitDpkg()
            inst, errors, code = yield utils.getProcessOutputAndValue(
                '/usr/bin/apt-get', args=('-q', '-y', '-o',
                'DPkg::Options::=--force-confold', 'install', data['package']),
                env=os.environ
            )

        defer.returnValue({
            'stdout': inst,
            'stderr': errors,
            'code': code
        })

    @defer.inlineCallbacks
    def _rhel_install(self, request, data):
        """
        Install a package from a url or rpm repo
        Accepts: {'package': str, ['url': str]}
        """
        if 'url' in data:
            url = data['url']
            log.msg('Package instalation %s requested from %s' % (
                url, request.getClientIP()))
            fn = url.split('/')[-1]
            # Download the file
            inst, errors, code = yield utils.getProcessOutputAndValue(
                '/usr/bin/wget', args=('-nv', '-c', '-O', '/tmp/'+fn, url))

            if code!=0:
                defer.returnValue({'error': inst+errors})
            else:
                # Install with gdebi (needs a full shell)
                inst, errors, code = yield utils.getProcessOutputAndValue(
                    '/usr/bin/yum', args=(
                        '--nogpgcheck', '-q', 'install', '/tmp/'+fn),
                    env=os.environ
                )
                os.unlink('/tmp/'+fn)
        else:
            log.msg('Package instalation %s requested from %s' % (
                data['package'], request.getClientIP()))
            # Update apt
            inst, errors, code = yield utils.getProcessOutputAndValue(
                '/usr/bin/yum', args=(
                    '-q', '--nogpgcheck', 'install', data['package']),
                env=os.environ
            )

        defer.returnValue({
            'stdout': inst,
            'stderr': errors,
            'code': code
        })

    def post_install(self, request, data):
        if self.os == 'Ubuntu':
            return self._ubuntu_install(request, data)
        else:
            return self._rhel_install(request, data)

    @defer.inlineCallbacks
    def get_supervisor_stop(self, request, args):
        "Stop a supervisor process"
        process = args[0]

        log.msg('Stopping supervisor proccess %s' % process)

        out, code = yield self.runShell(
            'supervisorctl stop %s' % process
        )

        defer.returnValue({'stdout': out})

    @defer.inlineCallbacks
    def get_supervisor_start(self, request, args):
        "Start a supervisor process"
        process = args[0]

        log.msg('Starting supervisor proccess %s' % process)

        out, code = yield self.runShell(
            'supervisorctl start %s' % process
        )

        defer.returnValue({'stdout': out})

    @defer.inlineCallbacks
    def get_supervisor_update(self, request):
        "Update supervisor configuration"
        log.msg('Updating supervisor configuration')

        out, code = yield self.runShell(
            'supervisorctl update'
        )

        defer.returnValue({'stdout': out})

    @defer.inlineCallbacks
    def get_all_stop(self, request):
        """
        Stop all public services
        """
        log.msg('All stop requested from %s' % (request.getClientIP()))

        out, code = yield self.runShell(
            'stop cron; /etc/init.d/nginx stop; supervisorctl stop all'
        )

        defer.returnValue({'stdout': out})

    @defer.inlineCallbacks
    def get_all_start(self, request):
        """
        Start all public services
        """
        log.msg('All start requested from %s' % (request.getClientIP()))

        out, code = yield self.runShell(
            'supervisorctl update; supervisorctl start all; /etc/init.d/nginx start; start cron'
        )

        defer.returnValue({'stdout': out})

    @defer.inlineCallbacks
    def get_puppet_run(self, request):
        """
        Start a puppet agent run
        """
        log.msg('Puppet run requested from %s' % (request.getClientIP()))

        out, code = yield self.runShell(
            '/usr/bin/puppet agent --onetime --no-daemonize --ignorecache --logdest syslog'
        )

        defer.returnValue({'stdout': out})

"""Generic Weibo base class for all workers that run on hosts."""

import errno
import inspect
import os
import random
import signal
import sys
import time

import eventlet
import greenlet

from weibo.common import cfg
from weibo.common import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

class SignalExit(SystemExit):
    def __init__(self, signo, exccode=1):
        super(SignalExit, self).__init__(exccode)
        self.signo = signo

class Launcher(object):
    """Launch one or more services and wait for them to complete."""

    def __init__(self):
        """Initialize the service launcher.

        :returns: None

        """
        self._services = []
        eventlet_backdoor.initialize_if_enabled()

    @staticmethod
    def run_server(server):
        """Start and wait for a server to finish.

        :param service: Server to run and wait for.
        :returns: None

        """
        server.start()
        server.wait()

    def launch_server(self, server):
        """Load and start the given server.

        :param server: The server you would like to start.
        :returns: None

        """
        gt = eventlet.spawn(self.run_server, server)
        self._services.append(gt)

    def stop(self):
        """Stop all services which are currently running.

        :returns: None

        """
        for service in self._services:
            service.kill()

    def wait(self):
        """Waits until all services have been stopped, and then returns.

        :returns: None

        """
        for service in self._services:
            try:
                service.wait()
            except greenlet.GreenletExit:
                pass


class ServiceLauncher(Launcher):
    def _handle_signal(self, signo, frame):
        # Allow the process to be killed again and die from natural causes
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        raise SignalExit(signo)

    def wait(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        status = None
        try:
            super(ServiceLauncher, self).wait()
        except SignalExit as exc:
            signame = {signal.SIGTERM: 'SIGTERM',
                       signal.SIGINT: 'SIGINT'}[exc.signo]
            LOG.info(_('Caught %s, exiting'), signame)
            status = exc.code
        except SystemExit as exc:
            status = exc.code
        finally:
            self.stop()

        if status is not None:
            sys.exit(status)


class ServerWrapper(object):
    def __init__(self, server, workers):
        self.server = server
        self.workers = workers
        self.children = set()
        self.forktimes = []


class ProcessLauncher(object):
    def __init__(self):
        self.children = {}
        self.sigcaught = None
        self.running = True
        rfd, self.writepipe = os.pipe()
        self.readpipe = eventlet.greenio.GreenPipe(rfd, 'r')

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signo, frame):
        self.sigcaught = signo
        self.running = False

        # Allow the process to be killed again and die from natural causes
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def _pipe_watcher(self):
        # This will block until the write end is closed when the parent
        # dies unexpectedly
        self.readpipe.read()

        LOG.info(_('Parent process has died unexpectedly, exiting'))

        sys.exit(1)


































# NOTE(vish): the global launcher is to maintain the existing
#             functionality of calling service.serve +
#             service.wait
_launcher = None


def serve(server, workers=None):
    global _launcher
    if _launcher:
        raise RuntimeError('serve() can only be called once')

    if workers:
        _launcher = ProcessLauncher()
        _launcher.launch_server(server, workers=workers)
    else:
        _launcher = ServiceLauncher()
        _launcher.launch_server(server)


def wait():
    _launcher.wait()

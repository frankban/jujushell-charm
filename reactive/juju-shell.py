import os
import subprocess

from charms.reactive import (
    hook,
    set_state,
)
from charmhelpers.core.templating import render
from charmhelpers.core.hookenv import (
    open_port,
    status_set,
)


FILES = os.path.join(os.getcwd(), 'files')


@hook('install')
def install_service():
    """Installs the juju-shell systemd service."""
    render('juju-shell.service',
           '/usr/lib/systemd/user/juju-shell.service',
           {'juju_shell': os.path.join(FILES, 'juju-shell', 'juju-shell.py')},
           perms=664)
    try:
        subprocess.check_call(('systemctl', 'enable',
                               '/usr/lib/systemd/user/juju-shell.service'))
    except:
        status_set('blocked', 'error enabling juju-shell.service')
    try:
        subprocess.check_call(('systemctl', 'daemon-reload'))
    except:
        status_set('blocked', 'error reloading systemd daemon')
    set_state('juju-shell.installed')


@hook('start')
def install_deps():
    """Installs the python deps for terminado."""
    reqs = os.path.join(FILES, 'requirements.txt')
    try:
        subprocess.check_call(('pip', 'install', '-r', reqs))
    except:
        status_set('blocked', 'error installing python deps from pypi')
    # For now, open the port on which terminado is running. This is 8765 instead
    # of 80 so that the service can be run as ubuntu, rather than root. This
    # Will be changed when we run the WS proxy.
    open_port(8765)
    restart()


@hook('start')
@hook('config-changed')
def restart():
    """Restarts the juju-shell service."""
    try:
        subprocess.check_call(('systemctl', 'restart', 'juju-shell.service'))
    except:
        status_set('blocked', 'error (re)starting juju shell service')


@hook('stop')
def stop():
    """Stops the juju-shell service."""
    try:
        subprocess.check_call(('systemctl', 'stop', 'juju-shell.service'))
    except:
        status_set('blocked', 'error stopping juju shell service')

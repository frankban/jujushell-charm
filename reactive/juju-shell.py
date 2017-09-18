import subprocess
from charms.reactive import (
    hook,
    set_state,
)
from charmhelpers.core.templating import render
from charmhelpers.core.hookenv import status_set


@hook('install')
def install():
    render('juju-shell.service',
           '/usr/lib/systemd/user/juju-shell.service',
           {'juju-shell': os.path.join(
               os.getcwd(), 'files', 'juju-shell', 'juju-shell.py')},
           perms='664')
    subprocess.check_call(('systemctl', 'daemon-reload'))
    set_state('juju-shell.installed')


@hook('start')
@hook('config-changed')
def restart():
    try:
        subprocess.check_call(('systemctl', 'restart', 'juju-shell.service'))
    except:
        status_set('error', 'error (re)starting juju shell service')


@hook('stop')
def stop():
    try:
        subprocess.check_call(('systemctl', 'stop', 'juju-shell.service'))
    except:
        status_set('error', 'error (re)starting juju shell service')

import os
import subprocess

from charmhelpers.core.hookenv import (
    open_port,
    status_set,
)
from charmhelpers.core.templating import render
from charms.reactive import (
    hook,
    remove_state,
    set_state,
)
import yaml


FILES = os.path.join(os.getcwd(), 'files')


@hook('install')
def install_service():
    """Installs the jujushell systemd service."""
    render('jujushell.service',
           '/usr/lib/systemd/user/jujushell.service',
           {
               'jujushell': os.path.join(FILES, 'jujushell'),
               'jujushell_config': os.path.join(FILES, 'config.yaml'),
           },
           perms=775)
    api_addrs = os.environ.get('JUJU_API_ADDRESSES')
    if api_addrs is None:
        raise ValueError("Could not find API addresses")
    api_addrs = api_addrs.split()
    render('config.yaml', os.path.join(FILES, 'config.yaml'),
           {'api_addrs': yaml.safe_dump(api_addrs)})
    subprocess.check_call(('systemctl', 'enable',
                           '/usr/lib/systemd/user/jujushell.service'))
    subprocess.check_call(('systemctl', 'daemon-reload'))
    set_state('jujushell.installed')


@hook('start')
def install_deps():
    # For now, open the port on which terminado is running. This is 8765 instead
    # of 80 so that the service can be run as ubuntu, rather than root. This
    # Will be changed when we run the WS proxy.
    open_port(8047)
    restart()


@hook('start')
@hook('config-changed')
def restart():
    """Restarts the jujushell service."""
    subprocess.check_call(('systemctl', 'restart', 'jujushell.service'))
    status_set('active', 'jujushell started')
    set_state('jujushell.started')
    remove_state('jujushell.stopped')


@hook('stop')
def stop():
    """Stops the jujushell service."""
    subprocess.check_call(('systemctl', 'stop', 'jujushell.service'))
    remove_state('jujushell.started')
    set_state('jujushell.stopped')

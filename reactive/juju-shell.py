import os
import subprocess

from charmhelpers.core.hookenv import (
    close_port,
    config,
    log,
    open_port,
    resource_get,
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
IMAGE_NAME = 'termserver'


def build_config():
    """Build the jujushell config server."""
    log('building jujushell config.yaml')
    cfg = config()
    api_addrs = os.environ.get('JUJU_API_ADDRESSES')
    if api_addrs is None:
        raise ValueError("Could not find API addresses")
    api_addrs = api_addrs.split()
    render('config.yaml', os.path.join(FILES, 'config.yaml'),
           {
               'api_addrs': yaml.safe_dump(api_addrs),
               'image_name': IMAGE_NAME,
               'port': cfg['port'],
           })

@hook('install')
def install_service():
    """Installs the jujushell systemd service."""
    # Render the jujushell systemd service module.
    log('creating systemd module')
    render('jujushell.service',
           '/usr/lib/systemd/user/jujushell.service',
           {
               'jujushell': os.path.join(FILES, 'jujushell'),
               'jujushell_config': os.path.join(FILES, 'config.yaml'),
           },
           perms=775)

    # Retrive the lxc image from the the resource and import it.
    log('fetching lxc image')
    resource = resource_get('termserver')
    if not resource:
        raise ValueError("Could not retrieve termserver resource")
    subprocess.check_call(('lxc', 'image', 'import', resource,
                           '--alias={}'.format(IMAGE_NAME)))

    # Build the configuration file for jujushell.
    build_config()

    # Enable the jujushell module.
    log('enabling systemd module')
    subprocess.check_call(('systemctl', 'enable',
                           '/usr/lib/systemd/user/jujushell.service'))
    subprocess.check_call(('systemctl', 'daemon-reload'))
    set_state('jujushell.installed')


@hook('start')
@hook('config-changed')
def restart():
    """Restarts the jujushell service."""
    log('(re)starting the jujushell service')
    subprocess.check_call(('systemctl', 'restart', 'jujushell.service'))
    status_set('active', 'jujushell started')
    set_state('jujushell.started')
    remove_state('jujushell.stopped')


@hook('config-changed')
def manage_ports():
    """Opens the port on which to listen, closing the previous if needed."""
    cfg = config()
    if cfg.change('port'):
        log('port updated from {} to {}'.format(
            cfg.previous('port'), cfg['port']))
        close_port(cfg.previous('port'))
    open_port(cfg['port'])
    build_config()


@hook('stop')
def stop():
    """Stops the jujushell service."""
    subprocess.check_call(('systemctl', 'stop', 'jujushell.service'))
    remove_state('jujushell.started')
    set_state('jujushell.stopped')

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
        raise ValueError('Could not find API addresses')
    api_addrs = api_addrs.split()
    render('config.yaml', os.path.join(FILES, 'config.yaml'), {
        'api_addrs': yaml.safe_dump(api_addrs),
        'image_name': IMAGE_NAME,
        'port': cfg['port'],
        'log_level': cfg['log-level'],
    })


def manage_ports():
    """Opens the port on which to listen, closing the previous if needed."""
    cfg = config()
    if cfg.changed('port'):
        log('port updated from {} to {}'.format(
            cfg.previous('port'), cfg['port']))
        close_port(cfg.previous('port'))
    open_port(cfg['port'])
    build_config()


@hook('install')
def install_service():
    """Installs the jujushell systemd service."""
    # Render the jujushell systemd service module.
    status_set('maintenance', 'creating systemd module')
    render('jujushell.service', '/usr/lib/systemd/user/jujushell.service', {
        'jujushell': os.path.join(FILES, 'jujushell'),
        'jujushell_config': os.path.join(FILES, 'config.yaml'),
    }, perms=775)

    # Retrieve the jujushell binary resource.
    resource = resource_get('jujushell')
    if not resource:
        raise ValueError('Could not retrieve jujushell resource')
    os.rename(resource, os.path.join(FILES, 'jujushell'))
    os.chmod(os.path.join(FILES, 'jujushell'), 0o775)

    # Retrieve the LXD image from the the resource and import it.
    status_set('maintenance', 'fetching LXD image')
    subprocess.check_call(('lxd', 'init', '--auto'))
    resource = resource_get('termserver')
    if not resource:
        raise ValueError('Could not retrieve termserver resource')
    try:
        # Catch an exception here in case we are retrying this hook.
        subprocess.check_call(('lxc', 'image', 'delete', IMAGE_NAME))
    except:
        log('image does not yet exist')
    subprocess.check_call((
        'lxc', 'image', 'import', resource, '--alias={}'.format(IMAGE_NAME)))

    # Build the configuration file for jujushell.
    build_config()

    # Enable the jujushell module.
    status_set('maintenance', 'enabling systemd module')
    subprocess.check_call((
        'systemctl', 'enable', '/usr/lib/systemd/user/jujushell.service'))
    subprocess.check_call(('systemctl', 'daemon-reload'))
    set_state('jujushell.installed')
    status_set('maintenance', 'jujushell installed')


@hook('start')
def start():
    restart()


@hook('config-changed')
def config_changed():
    restart()


def restart():
    """Restarts the jujushell service."""
    status_set('maintenance', '(re)starting the jujushell service')
    manage_ports()
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

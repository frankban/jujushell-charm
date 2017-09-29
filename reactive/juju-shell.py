import os
import pipes
import subprocess
import time

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
    only_once,
    remove_state,
    set_state,
    when,
)
import yaml


CURDIR = os.getcwd()
FILES = os.path.join(CURDIR, 'files')
AGENT = os.path.join(CURDIR, '..', 'agent.conf')
IMAGE_NAME = 'termserver'
LXC = '/snap/bin/lxc'
BRIGE_NAME = 'jujushellbr0'


def call(command, *args):
    """Call a subprocess passing the given arguments.

    Take the subcommand and its parameters as args.
    Raise an OSError with the error output in case of failure.
    """
    pipe = subprocess.PIPE
    cmd = (command,) + args
    cmdline = ' '.join(map(pipes.quote, cmd))
    log('Running the following: {!r}'.format(cmdline))
    try:
        process = subprocess.Popen(cmd, stdin=pipe, stdout=pipe, stderr=pipe)
    except OSError as err:
        raise OSError('Command {!r} not found: {}'.format(command, err))
    output, error = map(lambda msg: msg.decode('utf-8'), process.communicate())
    if process.poll():
        raise OSError(
            'Command {!r} failed: {!r}'.format(cmdline, output + error))
    log('Command {!r} succeeded: {}'.format(cmdline, output))


def build_config():
    """Build the jujushell config server."""
    log('building jujushell config.yaml')
    api_addrs = os.environ.get('JUJU_API_ADDRESSES')
    if api_addrs is None:
        raise ValueError('Could not find API addresses')
    cfg = config()
    data = {
        'juju-addrs': api_addrs.split(),
        'juju-cert': get_juju_cert(AGENT),
        'image-name': IMAGE_NAME,
        'log-level': cfg['log-level'],
        'port': cfg['port'],
    }
    with open(os.path.join(FILES, 'config.yaml'), 'w') as stream:
        yaml.safe_dump(data, stream=stream)


def get_juju_cert(path):
    """Return the certificate to use when connecting to the controller.

    The certificate is provided in PEM format and it is retrieved by parsing
    agent.conf.
    """
    with open(path) as stream:
        return yaml.safe_load(stream)['cacert']


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
    # Build the configuration file for jujushell.
    build_config()
    # Enable the jujushell module.
    status_set('maintenance', 'enabling systemd module')
    call('systemctl', 'enable', '/usr/lib/systemd/user/jujushell.service')
    call('systemctl', 'daemon-reload')
    set_state('jujushell.installed')
    status_set('maintenance', 'jujushell installed')


@when('snap.installed.lxd')
@only_once
def setup_lxd():
    """Configure LXD."""
    status_set('maintenance', 'fetching LXD image')
    resource = resource_get('termserver')
    if not resource:
        raise ValueError('Could not retrieve termserver resource')
    try:
        # Catch an exception here in case we are retrying this hook.
        call(LXC, 'image', 'delete', IMAGE_NAME)
    except:
        log('image does not yet exist')
    os.rename(resource, '/tmp/termserver.tar.gz')

    status_set('maintenance', 'setting up LXD')
    # Wait for the LXD daemon to be up and running.
    # TODO: we can do better than time.sleep().
    time.sleep(10)
    call(os.path.join(FILES, 'setup-lxd.sh'))

    status_set('maintenance', 'configuring ubuntu user')
    call('adduser', 'ubuntu', 'lxd')


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
    call('systemctl', 'restart', 'jujushell.service')
    status_set('active', 'jujushell started')
    set_state('jujushell.started')
    remove_state('jujushell.stopped')


@hook('stop')
def stop():
    """Stops the jujushell service."""
    call('systemctl', 'stop', 'jujushell.service')
    remove_state('jujushell.started')
    set_state('jujushell.stopped')

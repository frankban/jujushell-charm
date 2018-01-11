# Copyright 2017 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

import base64
import hashlib
import os
import pipes
import subprocess
from urllib import parse

from charmhelpers.core import (
    hookenv,
    templating,
)
from charms.reactive import (
    set_flag,
)
import pylxd
import yaml


# Define the LXD image name and profiles to use when launching instances.
IMAGE_NAME = 'termserver'
PROFILE_DEFAULT, PROFILE_TERMSERVER = 'default', 'termserver-limited'


def agent_path():
    """Get the location for the unit's agent file."""
    return os.path.join(hookenv.charm_dir(), '..', 'agent.conf')


def config_path():
    """Get the location for the configuration file."""
    return os.path.join(hookenv.charm_dir(), 'files', 'config.yaml')


def jujushell_path():
    """Get the location for the jujushell binary."""
    return os.path.join(hookenv.charm_dir(), 'files', 'jujushell')


def termserver_path(limited=False):
    """Get the location for the termserver image."""
    return '/var/tmp/termserver{}.tar.gz'.format('-limited' if limited else '')


def call(command, *args, **kwargs):
    """Call a subprocess passing the given arguments.

    Take the subcommand and its parameters as args.
    Raise an OSError with the error output in case of failure.
    """
    pipe = subprocess.PIPE
    cmd = (command,) + args
    cmdline = ' '.join(map(pipes.quote, cmd))
    hookenv.log('running the following: {!r}'.format(cmdline))
    try:
        process = subprocess.Popen(
            cmd, stdin=pipe, stdout=pipe, stderr=pipe, **kwargs)
    except OSError as err:
        raise OSError('command {!r} not found: {}'.format(command, err))
    output, error = map(lambda msg: msg.decode('utf-8'), process.communicate())
    retcode = process.poll()
    if retcode:
        msg = 'command {!r} failed with retcode {}: {!r}'.format(
            cmdline, retcode, output + error)
        hookenv.log(msg)
        raise OSError(msg)
    hookenv.log('command {!r} succeeded: {!r}'.format(cmdline, output))


def build_config(cfg):
    """Build and save the jujushell server config."""
    juju_addrs = (
        _get_string(cfg, 'juju-addrs') or
        os.getenv('JUJU_API_ADDRESSES'))
    if not juju_addrs:
        raise ValueError('could not find API addresses')
    juju_cert = _get_string(cfg, 'juju-cert')
    if juju_cert == 'from-unit':
        juju_cert = _get_juju_cert(agent_path())

    current_port = get_port(cfg)
    # TODO: it's very unfortunate that charm helpers do not allow to get the
    # previous config as a dict.
    previous_cfg = getattr(cfg, '_prev_dict', {}) or {}
    previous_port = get_port(previous_cfg)
    hookenv.open_port(current_port)
    if previous_port and previous_port != current_port:
        hookenv.close_port(previous_port)

    data = {
        'juju-addrs': juju_addrs.split(),
        'juju-cert': juju_cert,
        'image-name': IMAGE_NAME,
        'log-level': cfg['log-level'],
        'port': current_port,
        'profiles': (PROFILE_DEFAULT, PROFILE_TERMSERVER),
    }
    if cfg['tls']:
        data.update(_build_tls_config(cfg))
    with open(config_path(), 'w') as stream:
        yaml.safe_dump(data, stream=stream)


def _build_tls_config(cfg):
    """Return jujushell server config related to TLS."""
    dns_name = _get_string(cfg, 'dns-name')
    if dns_name:
        # Let's Encrypt is used for managing certificates.
        return {'dns-name': dns_name}
    cert, key = cfg['tls-cert'], cfg['tls-key']
    if cert != "" and key != "":
        # Keys have been provided as options.
        return {
            'tls-cert': base64.b64decode(cert).decode('utf-8'),
            'tls-key': base64.b64decode(key).decode('utf-8'),
        }
    # Automatically generate a self-signed certificate.
    key, cert = _get_self_signed_cert()
    return {'tls-cert': cert, 'tls-key': key}


def get_port(cfg):
    """Return the port to use for exposing the jujushell service."""
    if cfg.get('tls') and _get_string(cfg, 'dns-name'):
        return 443
    return cfg.get('port')


def update_lxc_quotas(cfg):
    """Update the default profile to include resource limits from charm
    config."""
    call('/snap/bin/lxc', 'profile', 'set', 'default', 'limits.cpu',
         _get_string(cfg, 'lxc-quota-cpu-cores'))
    call('/snap/bin/lxc', 'profile', 'set', 'default',
         'limits.cpu.allowance',
         _get_string(cfg, 'lxc-quota-cpu-allowance'))
    call('/snap/bin/lxc', 'profile', 'set', 'default', 'limits.memory',
         _get_string(cfg, 'lxc-quota-ram'))
    call('/snap/bin/lxc', 'profile', 'set', 'default', 'limits.processes',
         _get_string(cfg, 'lxc-quota-processes'))


def _get_string(cfg, key):
    value = str(cfg.get(key, '') or '')
    return value.strip()


def _get_juju_cert(path):
    """Return the certificate to use when connecting to the controller.

    The certificate is provided in PEM format and it is retrieved by parsing
    agent.conf.
    """
    with open(path) as stream:
        return yaml.safe_load(stream)['cacert']


def _get_self_signed_cert():
    """Create and return a self signed TLS certificate."""
    call('openssl', 'req',
         '-x509',
         '-newkey', 'rsa:4096',
         '-keyout', 'key.pem',
         '-out', 'cert.pem',
         '-days', '365',
         '-nodes',
         '-subj', '/C=/ST=/L=/O=/OU=/CN=0.0.0.0')
    with open('key.pem') as keyfile:
        key = keyfile.read()
    with open('cert.pem') as certfile:
        cert = certfile.read()
    os.remove('cert.pem')
    os.remove('key.pem')
    return key, cert


def save_resource(name, path):
    """Retrieve a resource with the given name and save it in the given path.

    Raise an OSError if the resource cannot be retrieved.
    """
    hookenv.log('retrieving resource {!r}'.format(name))
    resource = hookenv.resource_get(name)
    if not resource:
        msg = 'cannot retrieve resource {!r}'.format(name)
        hookenv.log(msg)
        raise OSError(msg)
    os.rename(resource, path)
    hookenv.log('resource {!r} saved at {!r}'.format(name, path))
    set_flag('jujushell.resource.available.{}'.format(name))


def install_service():
    """Installs the jujushell systemd service."""
    # Render the jujushell systemd service module.
    hookenv.status_set('maintenance', 'creating systemd module')
    templating.render(
        'jujushell.service', '/usr/lib/systemd/user/jujushell.service', {
            'jujushell': jujushell_path(),
            'jujushell_config': config_path(),
        }, perms=775)
    # Build the configuration file for jujushell.
    hookenv.log('building jujushell config.yaml after installing service')
    build_config(hookenv.config())
    # Enable the jujushell module.
    hookenv.status_set('maintenance', 'enabling systemd module')
    call('systemctl', 'enable', '/usr/lib/systemd/user/jujushell.service')
    call('systemctl', 'daemon-reload')
    set_flag('jujushell.service.installed')
    hookenv.status_set('maintenance', 'jujushell installed')


def import_lxd_image(name, path):
    """Import the image with the given name from the given path into lxd."""
    # Load the whole file into memory as this is necessary when creating the
    # image.
    with open(path, 'rb') as f:
        data = f.read()
    h = hashlib.sha256()
    h.update(data)
    fingerprint = h.hexdigest()
    hookenv.log('{} has fingerprint {}'.format(path, fingerprint))

    client = _lxd_client()
    image = None
    alias = None
    for img in client.images.all():
        if img.fingerprint == fingerprint:
            hookenv.log('image {} already exists'.format(fingerprint))
            image = img
        for al in img.aliases:
            if al.get('name') == name:
                hookenv.log('alias {} currently refers to image {}'.format(
                    name,
                    img.fingerprint))
                alias = img
    if image is None:
        hookenv.status_set('maintenance',
                           'importing image {}'.format(fingerprint))
        image = client.images.create(data, wait=True)
    if alias is None:
        image.add_alias(name, '')
    elif alias.fingerprint != fingerprint:
        alias.delete_alias(name)
        image.add_alias(name, '')
    set_flag('jujushell.lxd.image.imported.{}'.format(name))


def _lxd_client():
    """Get a client connection to the LXD server."""
    return pylxd.client.Client('http+unix://{}'.format(
        parse.quote(_LXD_SOCKET, safe='')))


_LXD_SOCKET = '/var/snap/lxd/common/lxd/unix.socket'


def setup_lxd():
    """Configure LXD."""
    # When running LXD commands, use a working directory that's surely
    # available also from the perspective of confined LXD.
    cwd = '/'
    client = _lxd_client()
    initialized = False
    for net in client.networks.all():
        if net.name == 'jujushellbr0':
            initialized = True
            break
    if not initialized:
        call(_LXD_INIT_COMMAND, shell=True, cwd=cwd)
    call(_LXD_WAIT_COMMAND, shell=True, cwd=cwd)
    set_flag('jujushell.lxd.configured')


# Define the command used to initialize LXD.
_LXD_INIT_COMMAND = """
cat <<EOF | /snap/bin/lxd init --preseed
networks:
- name: jujushellbr0
  type: bridge
  config:
    ipv4.address: auto
    ipv6.address: none
storage_pools:
- name: data
  driver: zfs
profiles:
- name: {default}
  devices:
    root:
      path: /
      pool: data
      type: disk
    eth0:
      name: eth0
      nictype: bridged
      parent: jujushellbr0
      type: nic
- name: {termserver}
  config:
    user.user-data: |
      #cloud-config
      users:
      - name: ubuntu
        shell: /bin/bash
EOF
""".format(default=PROFILE_DEFAULT, termserver=PROFILE_TERMSERVER)
_LXD_WAIT_COMMAND = '/snap/bin/lxd waitready --timeout=30'


def exterminate_containers():
    client = _lxd_client()
    for container in client.containers.all():
        # XXX j.c.sackett 2017-11-28 When the pylxd version in the repos is
        # 2.2.4 we can replace the suprocess call with calls to
        # container.stop(wait=True) and container.delete()
        call('/snap/bin/lxc', 'delete', '-f', container.name)

# Copyright 2017 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

import os
from charmhelpers.core import (
    hookenv,
    host,
)
from charms import apt
from charms.layer import (
    jujushell,
    snap,
)
from charms.reactive import (
    hook,
    only_once,
    remove_state,
    set_state,
    when,
    when_not,
)


@hook('install')
def install():
    set_state('jujushell.install')


@hook('upgrade-charm')
def upgrade_charm():
    remove_state('jujushell.resource.available.jujushell')
    remove_state('jujushell.resource.available.termserver')
    remove_state('jujushell.lxd.image.imported.termserver')
    set_state('jujushell.restart')


@hook('start')
def start():
    set_state('jujushell.start')


@hook('stop')
def stop():
    remove_state('jujushell.start')


@when('jujushell.install')
@when_not('snap.installed.lxd')
def install_lxd():
    hookenv.status_set('maintenance', 'installing lxd')
    snap.install('lxd')


@when('jujushell.install')
@when_not('apt.installed.zfsutils-linux')
def install_zfsutils():
    hookenv.status_set('maintenance', 'installing zfsutils-linux')
    apt.queue_install(['zfsutils-linux'])


@when('jujushell.install')
@when_not('jujushell.resource.available.jujushell')
def install_jujushell():
    hookenv.status_set('maintenance', 'fetching jujushell')
    path = jujushell.jujushell_path()
    try:
        jujushell.save_resource('jujushell', path)
        os.chmod(path, 0o775)
        # Allow for running jujushell on privileged ports.
        jujushell.call('setcap', 'CAP_NET_BIND_SERVICE=+eip', path)
    except OSError as err:
        hookenv.status_set(
            'blocked', 'jujushell resource not available: {}'.format(err))


@when('jujushell.install')
@when_not('jujushell.resource.available.termserver')
def install_termserver():
    hookenv.status_set('maintenance', 'fetching termserver')
    try:
        jujushell.save_resource(
            'termserver', jujushell.termserver_path())
        jujushell.save_resource(
            'limited-termserver', jujushell.termserver_path(limited=True))
    except OSError as err:
        hookenv.status_set(
            'blocked', 'termserver resource not available: {}'.format(err))


@when('jujushell.resource.available.jujushell')
@when_not('jujushell.service.installed')
def install_service():
    jujushell.install_service()


@when('snap.installed.lxd')
@when('apt.installed.zfsutils-linux')
@only_once
def setup_lxd():
    hookenv.status_set('maintenance', 'configuring lxd')
    host.add_user_to_group('ubuntu', 'lxd')
    jujushell.setup_lxd()


@when('jujushell.lxd.configured')
@when_not('jujushell.lxd.image.imported.termserver')
def import_image():
    hookenv.status_set('maintenance', 'importing termserver images')
    limited = hookenv.config()['limit-termserver']
    jujushell.import_lxd_image(
        'termserver', jujushell.termserver_path(limited=limited))


@when('jujushell.lxd.image.imported.termserver')
@when('jujushell.resource.available.jujushell')
@when('jujushell.service.installed')
@when('jujushell.start')
@when_not('jujushell.running')
def start_service():
    hookenv.status_set('maintenance', 'starting the jujushell service')
    host.service_start('jujushell')
    hookenv.status_set('active', 'jujushell running')
    remove_state('jujushell.restart')
    set_state('jujushell.running')


@when('jujushell.lxd.image.imported.termserver')
@when('jujushell.resource.available.jujushell')
@when('jujushell.service.installed')
@when('jujushell.restart')
def restart_service():
    hookenv.status_set('maintenance', 'starting the jujushell service')
    host.service_restart('jujushell')
    hookenv.status_set('active', 'jujushell running')
    remove_state('jujushell.restart')


@when('jujushell.running')
@when_not('jujushell.start')
def stop_service():
    host.service_stop('jujushell')
    remove_state('jujushell.running')


@when('config.changed')
def config_changed():
    config = hookenv.config()
    jujushell.build_config(config)
    jujushell.update_lxc_quotas(config)
    remove_state('jujushell.lxd.image.imported.termserver')
    set_state('jujushell.restart')


@when('website.available')
def website_available(website):
    config = hookenv.config()
    website.configure(port=jujushell.get_port(config))


@when('website.available')
@when('config.changed.port')
def website_port_changed(website):
    website_available(website)


@when('prometheus.available')
@when_not('prometheus.configured')
def prometheus_available(prometheus):
    config = hookenv.config()
    prometheus.configure(port=jujushell.get_port(config))
    set_state('prometheus.configured')


@when_not('prometheus.available')
@when('prometheus.configured')
def prometheus_unavailable():
    remove_state('prometheus.configured')

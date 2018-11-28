# Copyright 2017 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

import os
from charmhelpers.core import (
    hookenv,
    host,
)
from charms import apt
from charms.layer import jujushell
from charms.reactive import (
    is_flag_set,
    hook,
    only_once,
    clear_flag,
    set_flag,
    when,
    when_not,
)


@hook('install')
def install():
    # pylxd is installed here manually rather than using the apt layer or the
    # wheelhouse. The latter cannot be used as the package relies on C modules
    # to be compiled. The apt package is out of date, as we need the fix at
    # https://github.com/lxc/pylxd/issues/232 in xenial.
    # TODO(frankban) We can remove this in favor of installing via apt when
    # xenial is updated with the fixed package.
    jujushell.call('pip', 'install', 'pylxd==2.2.6')
    set_flag('jujushell.install')


@hook('upgrade-charm')
def upgrade_charm():
    clear_flag('jujushell.resource.available.jujushell')
    clear_flag('jujushell.resource.available.termserver')
    clear_flag('jujushell.lxd.image.imported.termserver')
    set_flag('jujushell.restart')


@hook('start')
def start():
    set_flag('jujushell.start')


@hook('stop')
def stop():
    clear_flag('jujushell.start')


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
        # TODO for now, we save both termserver resources. In the future, this
        # may be streamlined to only save one at a time as needed.
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


@when('jujushell.install')
@when('apt.installed.zfsutils-linux')
@only_once
def setup_lxd():
    hookenv.status_set('maintenance', 'configuring lxd')
    host.add_user_to_group('ubuntu', 'lxd')
    jujushell.setup_lxd()


@when('jujushell.lxd.configured')
@when('jujushell.resource.available.termserver')
@when('jujushell.resource.available.limited-termserver')
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
    clear_flag('jujushell.restart')
    set_flag('jujushell.running')


@when('jujushell.lxd.image.imported.termserver')
@when('jujushell.resource.available.jujushell')
@when('jujushell.service.installed')
@when('jujushell.restart')
def restart_service():
    hookenv.status_set('maintenance', 'starting the jujushell service')
    host.service_restart('jujushell')
    hookenv.status_set('active', 'jujushell running')
    clear_flag('jujushell.restart')


@when('jujushell.running')
@when_not('jujushell.start')
def stop_service():
    host.service_stop('jujushell')
    clear_flag('jujushell.running')


@when('config.changed')
def config_changed():
    config = hookenv.config()
    jujushell.build_config(config)
    if is_flag_set('jujushell.lxd.configured'):
        jujushell.update_lxc_quotas(config)
        clear_flag('jujushell.lxd.image.imported.termserver')
    set_flag('jujushell.restart')


@when('website.available')
def website_available(website):
    config = hookenv.config()
    # Multiple ports are only required when using Let's Encrypt. Since a
    # website relation is being established here, we can assume that the TLS
    # termination is done elsewhere.
    website.configure(port=jujushell.get_ports(config)[0])


@when('website.available')
@when('config.changed.port')
def website_port_changed(website):
    website_available(website)


@when('prometheus.available')
@when_not('prometheus.configured')
def prometheus_available(prometheus):
    config = hookenv.config()
    prometheus.configure(port=jujushell.get_ports(config)[0])
    set_flag('prometheus.configured')


@when_not('prometheus.available')
@when('prometheus.configured')
def prometheus_unavailable():
    clear_flag('prometheus.configured')

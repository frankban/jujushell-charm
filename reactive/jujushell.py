from charmhelpers.core import (
    hookenv,
)
from charms.layer import jujushell
from charms.reactive import (
    hook,
    only_once,
    when,
)


@hook('install')
def install_service():
    jujushell.install_service()


@hook('start')
def start():
    jujushell.start()


@hook('stop')
def stop():
    jujushell.stop()


@when('snap.installed.lxd')
@only_once
def setup_lxd():
    jujushell.setup_lxd()


@when('config.changed')
def config_changed():
    jujushell.config_changed()


@when('config.changed.port')
def port_changed():
    config = hookenv.config()
    hookenv.open_port(config('port'))
    if config.previous('port'):
        hookenv.close_port(config.previous('port'))


@when('website.available')
def website_available(website):
    website.configure(port=hookenv.config('port'))


@when('website.available')
@when('config.changed.port')
def website_port_changed(website):
    website_available(website)

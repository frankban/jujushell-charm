from charms.layer import jujushell
from charms.reactive import (
    hook,
    only_once,
    when,
)

@hook('install')
def install_service():
    jujushell.install_service()


@when('snap.installed.lxd')
@only_once
def setup_lxd():
    jujushell.setup_lxd()


@hook('start')
def start():
    jujushell.start()


@hook('config-changed')
def config_changed():
    jujushell.config_changed()


@hook('stop')
def stop():
    jujushell.stop()

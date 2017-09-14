from charms.reactive import (
    hook,
    set_state,
)

@hook('install')
def install():
    set_state('jaas-shell.installed')

# jujushell charm

A Juju charm for allowing access to the Juju CLI through WebSocket connections.

## States

This charm sets the following states:

* jujushell.installed --- set when the installed hook completes.
* jujushell.stopped --- set when the charm is stopped, removed when the jujushell service starts.
* jujushell.started --- set when the service is (re)started, removed when the service is stopped.

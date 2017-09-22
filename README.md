# juju-shell

A charm for allowing access to the Juju CLI through xterm.js. The charm spins up a [terminado]() server which listens to WebSocket connections and passes them to the CLI, allowing the user to access juju.

## States

This charm sets the following states:

* juju-shell.installed --- set when the installed hook completes.

## Current status

* As of 2017-09-21, this charm installs terminado and starts it listening, along with a webpage running xterm.js with minimal styling
* As of 2017-09-12, this charm simply installs juju on a fresh xenial system. This will require the user to run `juju register`/`juju login` once they have access to the terminal.

The next tasks are:

* Install and set up LXD, and have the terminado server run on a prepared LXD image with a simple WebSocket proxy to direct the user's commands to that
* Have the GUI recognize when this charm is added to the environment and have the xterm.js portion embedded in the GUI
* Pass macaroons to the charm so that the user does not need to register/login
* Add the ability to run commands on a unit via this setup and `juju ssh`
* Take over the world

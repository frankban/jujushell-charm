# Contributing


You will need charm tools to work with this charm:

    snap install charm

Once that's installed, you will need to set up your working directories:

    export JUJU_REPOSITORY=$HOME/charms
    export LAYER_PATH=$JUJU_REPOSITORY/layers
    export INTERFACE_PATH=$JUJU_REPOSITORY/interfaces

    mkdir -p $LAYER_PATH $INTERFACE_PATH

    cd $JUJU_REPOSITORY/layers

(change `JUJU_REPOSITORY` to wherever you need)

Clone this charm into your layers directory. Once you have cloned it, you will
be ready to start working on the charm.

## Building and deploying locally

When you are ready to deploy your charm to test or QA, you will need to build
it. In the charm directory, run:

    charm build

It will build the charm and tell you where it has been built (likely
`../../builds/juju-shell-charm`).

To deploy the charm locally, change to the above directory, and then deploy and
expose with the following:

    juju deploy ./juju-shell-charm --series=xenial
    juju expose juju-shell-charm

Once the charm is installed and exposed, you can view it at
`<charm-public-ip>:8765`

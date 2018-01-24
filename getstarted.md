## Completing Juju Shell setup

The Juju Shell requires a valid SSL certificate and it supports 
[Let's Encrypt](https://letsencrypt.org/) to auto load a certificate once the
DNS is set. Visit your domain provider or DNS tool for your domain and set up
a subdomain for your Juju Shell. You'll need the IP address of the exposed
Juju Shell unit.

    $ juju expose jujushell
    $ juju status jujushell

    Model    Controller  Cloud/Region     Version  SLA
    default  jujushell   google/us-east1  2.3.2    unsupported

    App        Version  Status   Scale  Charm      Store       Rev  OS      Notes
    jujushell           waiting    0/1  jujushell  jujucharms    3  ubuntu
    exposed

    Unit         Workload  Agent       Machine  Public address  Ports  Message
    jujushell/0  waiting   allocating  0        35.196.154.94          waiting for
    machine

    Machine  State    DNS            Inst id        Series  AZ          Message
    0        pending  35.196.154.94  juju-e62c69-0  xenial  us-east1-b  RUNNING

You want to pull the `Public Address` from the status of the Juju Shell and
set that to your DNS record.

    jujushell.mydomain.com.        IN      A       35.196.154.94

Make sure that the DNS change has propagated and that it's resolving properly.

    $ juju run --unit jujushell/0 -- dig jujushell.mydomain.com


Once that returns the new DNS information you can set the configuration on the
charm to trigger the Let's Encrypt SSL certificate.

    $ juju config jujushell dns-name=jujushell.mydomain.com


The final step is to configure the Juju GUI to use the Juju Shell charm at the
DNS address you setup. Configure the Juju Shell url by typing `shift-!` and
entering the DNS name into the field

    ____ DNS name for the Juju Shell.


Once the DNS name is entered and you hit `Save` the new Juju Shell icon will
appear int he header next to the sharing icon. Congrats on an embedded shell
into your Juju GUI.

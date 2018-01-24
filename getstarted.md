## Completing Juju Shell setup

The Juju Shell requires a valid SSL certificate and it supports 
[Let's Encrypt](https://letsencrypt.org/) to auto load a certificate once the
DNS is set. Visit your domain provider or DNS tool for your domain and set up
a subdomain for your Juju Shell. You'll need the IP address of the exposed
Juju Shell unit.

    $ juju expose jujushell
    $ juju status jujushell
    
    ...
    
    Unit         Workload  Agent       Machine  Public address  Ports  Message
    jujushell/0  waiting   allocating  0        35.196.154.94          waiting for
    machine
    
    ...


You want to pull the `Public Address` from the status of the Juju Shell and
set that to your DNS record.

    jujushell.*.  IN  A  35.196.154.94


Make sure that the DNS change has propagated and that it's resolving properly.

    $ juju run --unit jujushell/0 -- dig jujushell.*


Once that returns the new DNS information you can set the configuration on the
charm to trigger the Let's Encrypt SSL certificate.

    $ juju config jujushell dns-name=jujushell.*


The final step is to configure the Juju GUI to use the Juju Shell charm at the
DNS address you setup. Configure the Juju Shell url by typing `shift-!` and
entering the DNS name into the field. The GUI does attempt to find a Juju
Shell in the current model and if found it will already be filled in for you.
If it's not there fill in the same DNS name you set the Juju Shell charm to.

    ____ DNS name for the Juju Shell.


Once the DNS name is entered and you hit `Save` the new Juju Shell icon will
appear int he header next to the sharing icon. Congrats on an embedded shell
into your Juju GUI.

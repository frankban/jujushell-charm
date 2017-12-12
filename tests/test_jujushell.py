# Copyright 2017 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

import base64
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import (
    call,
    Mock,
    patch,
)

import yaml

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_layer = os.path.join(_root, 'lib', 'charms', 'layer')
sys.path.insert(0, _layer)

# jujushell can only be imported after the layer directory has been added to
# the python path.
import jujushell  # noqa: E402


@patch('charmhelpers.core.hookenv.log')
class TestCall(unittest.TestCase):

    def test_success(self, mock_log):
        # A command suceeds.
        jujushell.call('echo')
        self.assertEqual(2, mock_log.call_count)
        mock_log.assert_has_calls([
            call("running the following: 'echo'"),
            call("command 'echo' succeeded: '\\n'"),
        ])

    def test_multiple_arguments(self, mock_log):
        # A command with multiple arguments succeeds.
        jujushell.call('echo', 'we are the borg')
        self.assertEqual(2, mock_log.call_count)
        mock_log.assert_has_calls([
            call('running the following: "echo \'we are the borg\'"'),
            call('command "echo \'we are the borg\'" succeeded: '
                 '\'we are the borg\\n\''),
        ])

    def test_failure(self, mock_log):
        # An OSError is raise when the command fails.
        with self.assertRaises(OSError) as ctx:
            jujushell.call('ls', 'no-such-file')
        expected_error = 'command \'ls no-such-file\' failed with retcode 2:'
        obtained_error = str(ctx.exception)
        self.assertTrue(obtained_error.startswith(expected_error))
        mock_log.assert_has_calls([
            call("running the following: 'ls no-such-file'"),
            call(obtained_error),
        ])

    def test_invalid_command(self, mock_log):
        # An OSError is raised if the subprocess fails to find the provided
        # command in the PATH.
        with self.assertRaises(OSError) as ctx:
            jujushell.call('no-such-command')
        expected_error = (
            "command 'no-such-command' not found: [Errno 2] "
            "No such file or directory: 'no-such-command'"
        )
        self.assertTrue(str(ctx.exception).startswith(expected_error))
        mock_log.assert_has_calls([
            call("running the following: 'no-such-command'"),
        ])


class TestUpdateLXCQuotas(unittest.TestCase):

    def test_update_lxc_quotas(self):
        cfg = {
            'lxc-quota-cpu-cores': 1,
            'lxc-quota-cpu-allowance': '100%',
            'lxc-quota-ram': '256MB',
            'lxc-quota-processes': 100,
        }
        with patch('jujushell.call') as mock_call:
            jujushell.update_lxc_quotas(cfg)
        mock_call.assert_has_calls([
            call('/snap/bin/lxc', 'profile', 'set', 'default',
                 'limits.cpu', '1'),
            call('/snap/bin/lxc', 'profile', 'set', 'default',
                 'limits.cpu.allowance', '100%'),
            call('/snap/bin/lxc', 'profile', 'set', 'default',
                 'limits.memory', '256MB'),
            call('/snap/bin/lxc', 'profile', 'set', 'default',
                 'limits.processes', '100'),
        ])
        self.assertEqual(mock_call.call_count, 4)


class TestBuildConfig(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory where to execute the test.
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        # Switch to the temporary directory.
        cwd = os.getcwd()
        os.chdir(directory)
        self.addCleanup(os.chdir, cwd)
        # Also make charm files live in the temp dir.
        files = os.path.join(directory, 'files')
        os.mkdir(files)
        os.environ['CHARM_DIR'] = directory
        self.addCleanup(os.environ.pop, 'CHARM_DIR')
        # Add juju addresses as an environment variable.
        os.environ['JUJU_API_ADDRESSES'] = '1.2.3.4:17070 4.3.2.1:17070'
        self.addCleanup(os.environ.pop, 'JUJU_API_ADDRESSES')

    def get_config(self):
        """Return the YAML decoded configuration file that has been created."""
        with open('files/config.yaml') as configfile:
            return yaml.safe_load(configfile)

    def make_cert(self):
        """Make a testing key pair in the current directory."""
        with open('cert.pem', 'w') as certfile:
            certfile.write('my cert')
        with open('key.pem', 'w') as keyfile:
            keyfile.write('my key')

    def test_no_tls(self):
        # The configuration file is created correctly without TLS.
        jujushell.build_config({
            'log-level': 'info',
            'port': 4247,
            'tls': False,
        })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4:17070', '4.3.2.1:17070'],
            'juju-cert': '',
            'log-level': 'info',
            'port': 4247,
            'profiles': ['default', 'termserver-limited'],
        }
        self.assertEqual(expected_config, self.get_config())

    def test_tls_provided(self):
        # Provided TLS keys are properly used.
        jujushell.build_config({
            'log-level': 'debug',
            'port': 80,
            'tls': True,
            'tls-cert': base64.b64encode(b'provided cert'),
            'tls-key': base64.b64encode(b'provided key'),
        })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4:17070', '4.3.2.1:17070'],
            'juju-cert': '',
            'log-level': 'debug',
            'port': 80,
            'profiles': ['default', 'termserver-limited'],
            'tls-cert': 'provided cert',
            'tls-key': 'provided key',
        }
        self.assertEqual(expected_config, self.get_config())

    def test_tls_provided_but_not_enabled(self):
        # Provided TLS keys are ignored when security is not enabled.
        jujushell.build_config({
            'log-level': 'debug',
            'port': 80,
            'tls': False,
            'tls-cert': base64.b64encode(b'provided cert'),
            'tls-key': base64.b64encode(b'provided key'),
        })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4:17070', '4.3.2.1:17070'],
            'juju-cert': '',
            'log-level': 'debug',
            'port': 80,
            'profiles': ['default', 'termserver-limited'],
        }
        self.assertEqual(expected_config, self.get_config())

    def test_tls_generated(self):
        # TLS keys are generated if not provided.
        self.make_cert()
        with patch('jujushell.call') as mock_call:
            jujushell.build_config({
                'log-level': 'trace',
                'port': 4247,
                'tls': True,
                'tls-cert': '',
                'tls-key': '',
            })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4:17070', '4.3.2.1:17070'],
            'juju-cert': '',
            'log-level': 'trace',
            'port': 4247,
            'profiles': ['default', 'termserver-limited'],
            'tls-cert': 'my cert',
            'tls-key': 'my key',
        }
        self.assertEqual(expected_config, self.get_config())
        # The right command has been executed.
        mock_call.assert_called_once_with(
            'openssl', 'req',
            '-x509',
            '-newkey', 'rsa:4096',
            '-keyout', 'key.pem',
            '-out', 'cert.pem',
            '-days', '365',
            '-nodes',
            '-subj', '/C=/ST=/L=/O=/OU=/CN=0.0.0.0')
        # Key files has been removed.
        self.assertEqual(['files'], os.listdir('.'))

    def test_tls_generated_when_key_is_missing(self):
        # TLS keys are generated if only one key is provided, not both.
        self.make_cert()
        with patch('jujushell.call'):
            jujushell.build_config({
                'log-level': 'trace',
                'port': 4247,
                'tls': True,
                'tls-cert': base64.b64encode(b'provided cert'),
                'tls-key': '',
            })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4:17070', '4.3.2.1:17070'],
            'juju-cert': '',
            'log-level': 'trace',
            'port': 4247,
            'profiles': ['default', 'termserver-limited'],
            'tls-cert': 'my cert',
            'tls-key': 'my key',
        }
        self.assertEqual(expected_config, self.get_config())

    def test_provided_juju_cert(self):
        # The configuration file is created with the provided Juju certificate.
        jujushell.build_config({
            'log-level': 'info',
            'juju-cert': 'provided cert',
            'port': 4247,
            'tls': False,
        })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4:17070', '4.3.2.1:17070'],
            'juju-cert': 'provided cert',
            'log-level': 'info',
            'port': 4247,
            'profiles': ['default', 'termserver-limited'],
        }
        self.assertEqual(expected_config, self.get_config())

    def test_juju_cert_from_agent_file(self):
        # A Juju certificate can be retrieved from the agent file in the unit.
        # Make agent file live in the temp dir.
        agent = os.path.join(os.environ['CHARM_DIR'], '..', 'agent.conf')
        with open(agent, 'w') as agentfile:
            yaml.safe_dump({'cacert': 'agent cert'}, agentfile)
        jujushell.build_config({
            'log-level': 'info',
            'juju-cert': 'from-unit',
            'port': 4247,
            'tls': False,
        })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4:17070', '4.3.2.1:17070'],
            'juju-cert': 'agent cert',
            'log-level': 'info',
            'port': 4247,
            'profiles': ['default', 'termserver-limited'],
        }
        self.assertEqual(expected_config, self.get_config())

    def test_provided_juju_addresses(self):
        # Juju addresses can be provided via the configuration.
        jujushell.build_config({
            'juju-addrs': '1.2.3.4/provided 4.3.2.1/provided',
            'log-level': 'info',
            'port': 4247,
            'tls': False,
        })
        expected_config = {
            'image-name': 'termserver',
            'juju-addrs': ['1.2.3.4/provided', '4.3.2.1/provided'],
            'juju-cert': '',
            'log-level': 'info',
            'port': 4247,
            'profiles': ['default', 'termserver-limited'],
        }
        self.assertEqual(expected_config, self.get_config())

    def test_error_no_juju_addresses(self):
        # A ValueError is raised if no Juju addresses can be retrieved.
        os.environ['JUJU_API_ADDRESSES'] = ''
        with self.assertRaises(ValueError) as ctx:
            jujushell.build_config({
                'log-level': 'info',
                'port': 4247,
                'tls': False,
            })
        self.assertEqual('could not find API addresses', str(ctx.exception))


@patch('charmhelpers.core.hookenv.log')
class TestSaveResource(unittest.TestCase):

    def test_resource_retrieved(self, mock_log):
        # A resource can be successfully retrieved and stored.
        with patch('charmhelpers.core.hookenv.resource_get') as mock_get:
            mock_get.return_value = ''
            with self.assertRaises(OSError) as ctx:
                jujushell.save_resource('bad-resource', 'mypath')
        self.assertEqual(
            "cannot retrieve resource 'bad-resource'", str(ctx.exception))
        mock_get.assert_called_once_with('bad-resource')

    def test_error_getting_resource(self, mock_log):
        # An OSError is raised if it's not possible to get a resource.
        # Create a directory for storing the resource.
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        resource = os.path.join(directory, 'resource')
        with open(resource, 'w') as resource_file:
            resource_file.write('resource content')
        # Create a target file where to save the resource.
        path = os.path.join(directory, 'target')
        with patch('charmhelpers.core.hookenv.resource_get') as mock_get:
            mock_get.return_value = resource
            jujushell.save_resource('myresource', path)
        # The target has been created with the right content.
        self.assertTrue(os.path.isfile(path))
        with open(path) as target_file:
            self.assertEqual('resource content', target_file.read())
        # The original resource file is no more.
        self.assertFalse(os.path.isfile(resource))
        mock_get.assert_called_once_with('myresource')


@patch('charmhelpers.core.hookenv.log')
class TestImportLXDImage(unittest.TestCase):

    def setUp(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        self.path = os.path.join(directory, 'image')
        with open(self.path, 'wb') as f:
            f.write(b'AAAAAAAAAA')

    def test_no_images(self, mock_log):
        with patch('jujushell._lxd_client') as mock_client:
            mock_client().images.all.return_value = ()
            jujushell.import_lxd_image('test', self.path)
        mock_client().images.create.assert_called_once_with(
            b'AAAAAAAAAA',
            wait=True)
        mock_client().images.create().add_alias.assert_called_once_with(
            'test',
            '')

    def test_image_exists(self, mock_log):
        image = Mock()
        image.fingerprint = \
            '1d65bf29403e4fb1767522a107c827b8884d16640cf0e3b18c4c1dd107e0d49d'
        image.aliases = [{'name': 'test', 'description': ''}]
        with patch('jujushell._lxd_client') as mock_client:
            mock_client().images.all.return_value = [image]
            jujushell.import_lxd_image('test', self.path)
        mock_client().images.create.assert_not_called()

    def test_image_exists_no_alias(self, mock_log):
        image = Mock()
        image.fingerprint = \
            '1d65bf29403e4fb1767522a107c827b8884d16640cf0e3b18c4c1dd107e0d49d'
        image.aliases = []
        with patch('jujushell._lxd_client') as mock_client:
            mock_client().images.all.return_value = [image]
            jujushell.import_lxd_image('test', self.path)
        mock_client().images.create.assert_not_called()
        image.add_alias.assert_called_once_with('test', '')

    def test_image_with_alias_exists(self, mock_log):
        image = Mock()
        image.fingerprint = \
            '2d65bf29403e4fb1767522a107c827b8884d16640cf0e3b18c4c1dd107e0d49d'
        image.aliases = [{'name': 'test', 'description': ''}]
        with patch('jujushell._lxd_client') as mock_client:
            mock_client().images.all.return_value = [image]
            jujushell.import_lxd_image('test', self.path)
        mock_client().images.create.assert_called_once_with(
            b'AAAAAAAAAA',
            wait=True)
        mock_client().images.create().add_alias.assert_called_once_with(
            'test',
            '')
        image.delete_alias.assert_called_once_with('test')


@patch('charmhelpers.core.hookenv.log')
class TestSetupLXD(unittest.TestCase):

    def test_not_initialized(self, mock_log):
        with patch('jujushell._lxd_client') as mock_client:
            mock_client().networks.all.return_value = ()
            with patch('jujushell.call') as mock_call:
                jujushell.setup_lxd()
        self.assertEqual(2, mock_call.call_count)
        mock_call.assert_has_calls([
            call(jujushell._LXD_INIT_COMMAND, shell=True, cwd='/'),
            call(jujushell._LXD_WAIT_COMMAND, shell=True, cwd='/'),
        ])

    def test_initialized(self, mock_log):
        with patch('jujushell._lxd_client') as mock_client:
            net = Mock()
            net.name = 'jujushellbr0'
            mock_client().networks.all.return_value = [net]
            with patch('jujushell.call') as mock_call:
                jujushell.setup_lxd()
        mock_call.assert_called_once_with(
            jujushell._LXD_WAIT_COMMAND, shell=True, cwd='/')


if __name__ == '__main__':
    unittest.main()

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import (
    call,
    patch,
)

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
        expected_error = (
            'command \'ls no-such-file\' failed with retcode 2: '
            '"ls: cannot access \'no-such-file\': '
            'No such file or directory\\n"'
        )
        self.assertEqual(expected_error, str(ctx.exception))
        mock_log.assert_has_calls([
            call("running the following: 'ls no-such-file'"),
            call(expected_error),
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
        self.assertEqual(expected_error, str(ctx.exception))
        mock_log.assert_has_calls([
            call("running the following: 'no-such-command'"),
        ])


class TestGetSelfSignedCert(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory where to execute the test.
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        # Switch to teh temporary directory.
        cwd = os.getcwd()
        os.chdir(directory)
        self.addCleanup(os.chdir, cwd)
        # Create cert files used for tests.
        with open('cert.pem', 'w') as certfile:
            certfile.write('my cert')
        with open('key.pem', 'w') as keyfile:
            keyfile.write('my key')

    def test_certificate_creation(self):
        # A certificate is correctly created and contents returned.
        with patch('subprocess.check_call') as mock_call:
            key, cert = jujushell.get_self_signed_cert()
        # The keys are successully returned.
        self.assertEqual('my key', key)
        self.assertEqual('my cert', cert)
        # The right command has been executed.
        mock_call.assert_called_once_with([
            'openssl', 'req',
            '-x509',
            '-newkey', 'rsa:4096',
            '-keyout', 'key.pem',
            '-out', 'cert.pem',
            '-days', '365',
            '-nodes',
            '-subj', '/C=/ST=/L=/O=/OU=/CN=0.0.0.0'])
        # Key files has been removed.
        self.assertEqual([], os.listdir('.'))


if __name__ == '__main__':
    unittest.main()

import sys
import ConfigParser
import unittest

sys.path.insert(0, '../../')

from loadbalancer.utils.kvm import RemoteKvm
from loadbalancer.utils.ssh_utils import SSH_Utils
from mock.mock import MagicMock

class Test_RemoteKvm(unittest.TestCase):

    def setUp(self):
        self.config = ConfigParser.RawConfigParser(allow_no_value=False)
        self.config.read('test_load_balancer.cfg')

        self.ssh_utils = SSH_Utils({})
        self.kvm = RemoteKvm(self.ssh_utils, self.config)
        self.host = self.config.get('infrastructure', 'hosts')
        self.instance_id = "9a22f664-bc68-44a0-b37b-4ac2a4e04a59"
        self.keypair = self.config.get('infrastructure', 'key')
        self.cap = 56000

    def tearDown(self):
        pass

    def test_retrive_cpu_cap_success(self):
        self.ssh_utils.run_and_get_result = MagicMock(return_value=self.cap)

        result_cap = self.kvm.retrive_cpu_cap(self.host, self.instance_id)

        self.assertEquals(result_cap, self.cap)

        command = "virsh schedinfo %s | grep vcpu_quota | awk '{print $3}'" % self.instance_id
        self.ssh_utils.run_and_get_result.assert_called_once_with(command, "root", self.host, self.keypair)

    def test_retrive_cpu_cap_virsh_returns_negative_1(self):
        self.ssh_utils.run_and_get_result = MagicMock(return_value="-1")

        result_cap = self.kvm.retrive_cpu_cap(self.host, self.instance_id)

        self.assertEquals(result_cap, -1)

        command = "virsh schedinfo %s | grep vcpu_quota | awk '{print $3}'" % self.instance_id
        self.ssh_utils.run_and_get_result.assert_called_once_with(command, "root", self.host, self.keypair)


if __name__ == "__main__":
    unittest.main()

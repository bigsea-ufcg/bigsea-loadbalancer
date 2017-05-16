from loadbalancer.service.heuristic.base import BaseHeuristic
from loadbalancer.utils.kvm import RemoteKvm
from loadbalancer.utils.ssh_utils import SSH_Utils

class ProActiveCap(BaseHeuristic):

    def __init__(self, **kwargs):
        self.ssh_utils = SSH_Utils({})
        self.monasca = kwargs['monasca']
        self.kvm = RemoteKvm(self.ssh_utils, kwargs['config'])
        if kwargs['provider'] == 'OpenStack':
            self.openstack = kwargs['openstack']

    def collect_information(self):
        hosts = self.openstack.available_hosts()

        metrics = {}
        for host in hosts:
            host_instances = self.openstack.get_host_instances(host)
            instances_info = {}
            cpu_cap_percentage = self.kvm.get_percentage_cpu_cap(host_instances)

        pass


    def decision(self):
        self.collect_information()
        pass

class RemoteKvm:

    def __init__(self, ssh_utils, config):
        self.ssh_utils = ssh_utils
        self.user = config.get('infrastructure', 'user')
        self.keypair = config.get('infrastructure', 'key')

    def retrive_cpu_cap(self, host, instance_id):
        virsh_command = ("virsh schedinfo %s | grep vcpu_quota | awk '{print $3}'" %
                   (instance_id))

        ssh_result = self.ssh_utils.run_and_get_result(virsh_command, "root", host, self.keypair)
        
        return int(ssh_result)

    def get_percentage_cpu_cap(self, host, instances):
        cap_percentage = {}
        for instance_id in instances:
            cpu_cap = self.retrive_cpu_cap(host, instance_id)
            if cpu_cap == -1 or cpu_cap == 100000:
                percentage = 100.0
            else:
                percentage = (cpu_cap/1000.)
            cap_percentage[instance_id] = percentage
        return cap_percentage

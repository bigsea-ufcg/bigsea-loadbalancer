from subprocess import check_output

class RemoteKvm:

    def __init__(self, config):
        self.user = config.get('infrastructure', 'user')
        self.keypair = config.get('infrastructure', 'key')

    def retrive_cpu_cap(self, host, instance_id):
        virsh_command = ("virsh schedinfo %s | grep vcpu_quota | awk '{print $3}'" %
                   (instance_id))
        ssh = ('ssh -o "StrictHostKeyChecking no" -i %s %s@%s' %
               (self.keypair, self.user, host))
        cpu_cap = check_output(ssh + virsh_command, shell=True)
        return cpu_cap

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
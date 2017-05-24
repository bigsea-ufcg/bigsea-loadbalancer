from loadbalancer.utils.logger import configure_logging, Log

import paramiko


class RemoteKvm:

    def __init__(self, config):
        self.user = config.get('infrastructure', 'user')
        self.keypair = config.get('infrastructure', 'key')
        self.logger = Log("KVM", "kvm_acess.log")
        configure_logging()

    def retrive_cpu_cap(self, host, instance_id):

        ssh = self._get_ssh_connection(host)
        virsh_command = (
            "virsh schedinfo %s | grep vcpu_quota | awk '{print $3}'" %
            (instance_id)
        )
        self.logger.log("Retrieving cpu_cap from instance %s in host %s" %
                        (instance_id, host))
        stdout = ssh.exec_command(virsh_command)[1].read()
        self.logger.log(stdout)
        ssh.close()
        return int(stdout)

    def get_percentage_cpu_cap(self, host, instances):
        cap_percentage = {}
        for instance_id in instances:
            cpu_cap = self.retrive_cpu_cap(host, instance_id)
            self.logger.log("Converting cpu_cap to percentage")
            if cpu_cap == -1 or cpu_cap == 100000:
                percentage = 1
            else:
                percentage = (cpu_cap / 100000.)
            cap_percentage[instance_id] = percentage
        return cap_percentage

    def _get_ssh_connection(self, host):
        keypair = paramiko.RSAKey.from_private_key_file(self.keypair)
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(hostname=host, username=self.user, pkey=keypair)
        self.logger.log("Created ssh connection to host %s" % host)
        return conn

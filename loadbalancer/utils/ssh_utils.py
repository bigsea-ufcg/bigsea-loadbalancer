import paramiko

class SSH_Utils(object):

    def __init__(self, hosts_ports):
        self.hosts_ports = hosts_ports

    def run_command(self, command, user, host, key):
        conn = self._get_ssh_connection(host, user, key)
        conn.exec_command(command)
 
    def run_and_get_result(self, command, user, host, key):
        conn = self._get_ssh_connection(host, user, key)
        stdout = conn.exec_command(command)[1]
        return stdout.read()
    
    def run_command_tunnel(self, command, user, host, key):
        conn = self._get_ssh_connection_tunnel(host, "root", key)
        conn.exec_command(command)
        
    def run_and_get_result_tunnel(self, command, user, host, key):
        conn = self._get_ssh_connection_tunnel(host, "root", key)
        stdout = conn.exec_command(command)[1]
        return stdout.read()

    def _get_ssh_connection(self, ip, username, keypair_path):
        keypair = paramiko.RSAKey.from_private_key_file(keypair_path)
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(hostname=ip, username=username, pkey=keypair)
        return conn
    
    def _get_ssh_connection_tunnel(self, ip, username, keypair_path):
        keypair = paramiko.RSAKey.from_private_key_file(keypair_path)
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(hostname="127.0.0.1", port=self.hosts_ports[ip], username=username, pkey=keypair)

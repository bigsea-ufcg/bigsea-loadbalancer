
from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client as nova_client


class OpenStackConnector(object):

    def __init__(self, configuration):
        self.configuration = configuration

    def __get_nova_client(self):
        auth = v3.Password(
            username=self.configuration.get('openstack', 'username'),
            password=self.configuration.get('openstack', 'password'),
            project_name=self.configuration.get('openstack', 'project_name'),
            user_domain_name=self.configuration.get('openstack',
                                                    'user_domain_name'),
            project_domain_name=self.configuration.get('openstack',
                                                       'project_domain_name'),
            auth_url=self.configuration.get('openstack', 'auth_url')
        )

        ks_session = session.Session(auth=auth)
        nova_conn = nova_client.Client('2', session=ks_session)
        return nova_conn

    def available_hosts(self):
        available_hosts = []
        nova = self.__get_nova_client()
        infra_hosts = self.configuration.get(
            'infrastructure', 'hosts'
        ).split(',')

        for host in nova.hosts.list():
            if host.host_name in infra_hosts:
                available_hosts.append(host.host_name)

        if not available_hosts:
            messsage = "Could not find any infrastructure hosts"
            raise Exception(messsage)

        return available_hosts

    def get_host_instances(self, host):
        nova = self.__get_nova_client()
        instances_ids = []
        opts = {'all_tenants': '1', 'host': host}
        for instance in nova.servers.list(search_opts=opts):
            instances_ids.append(instance.id)
        return instances_ids

    def hosts_free_resources(self, hosts):
        free_usage = {}
        nova = self.__get_nova_client()
        for host in hosts:
            for host_usage in nova.hosts.get(host):
                resource = host_usage._info['resource']
                if resource['project'] == '(total)':
                    total = resource.copy()
                    total.pop('project')
                    total.pop('host')
                if resource['project'] == '(used_now)':
                    used_now = resource.copy()
                    used_now.pop('project')
                    used_now.pop('host')
            free = {key: total[key] - used_now.get(key, 0) for key in total}
            free_usage[host] = free
        return free_usage

    def live_migration(self, instance_id, new_host):
        nova = self.__get_nova_client()
        instance = nova.servers.get(instance_id)
        host = instance.__getattr__('OS-EXT-SRV-ATTR:host')
        if host == new_host:
            return "Impossible to execute migration to same host"
        else:
            instance.live_migrate(host=new_host)
            return "Executing migration of instance %s from %s to %s" % (
                instance_id, host, new_host
            )

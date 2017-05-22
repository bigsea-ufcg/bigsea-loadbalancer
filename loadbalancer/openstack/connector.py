from loadbalancer.utils.logger import configure_logging, Log
from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client as nova_client



class OpenStackConnector(object):

    def __init__(self, configuration):
        self.logger = Log("OpenStackConnector", "openstack_connector.log")
        configure_logging()
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
        self.logger.log("Getting nova client")
        return nova_conn

    def available_hosts(self):
        self.logger.log("Looking for available hosts")
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
            self.logger.log("Could not find any infrastructure hosts")
            raise Exception(messsage)
        else:
            self.logger.log("Found hosts: %s" % str(available_hosts))
        return available_hosts

    def get_host_instances(self, host):
        self.logger.log("Getting instances from host %s" % host)
        nova = self.__get_nova_client()
        instances_ids = []
        opts = {'all_tenants': '1', 'host': host}
        for instance in nova.servers.list(search_opts=opts):
            instances_ids.append(instance.id)
        return instances_ids

    def hosts_resources(self, hosts):
        host_usages = {}
        nova = self.__get_nova_client()
        self.logger.log("Getting hosts resources usage")
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
            host_usages[host] = {'total': total, 'used_now': used_now}
        return host_usages

    def live_migration(self, migrations):
        nova = self.__get_nova_client()
        for instance_id in migrations:
            instance = nova.servers.get(instance_id)
            new_host = migrations[instance_id]
            host = instance.__getattr__('OS-EXT-SRV-ATTR:host')
            if host == new_host:
                self.logger.log(
                    "Impossible to execute migration of instance %s to same host" %
                    instance_id
                )
            else:
                self.logger.log(
                    "Executing migration of instance %s from %s to %s" %
                    (instance_id, host, new_host)
                )
                instance.live_migrate(host=new_host)
                self.logger.log("Finished migration")


    def get_flavor_information(self, instances):
        nova = self.__get_nova_client()
        instances_flavors = {}
        for instance_id in instances:
            instance = nova.servers.get(instance_id)
            flavor_id = instance.flavor['id']
            instances_flavors[instance_id] = nova.flavors.get(flavor_id)._info
            self.logger.log("Getting Flavor information for instance %s" %
                            instance_id)
        return instances_flavors

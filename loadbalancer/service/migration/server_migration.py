

from novaclient import client as nova_client
from keystoneauth1.identity import v3
from keystoneauth1 import session

import ConfigParser


class MigrateServer:

    def __init__(self):
        self.__config = ConfigParser.RawConfigParser()
        self.__config.read('load_balancer.cfg')
        self.__nova_conn = self.__get_nova_client()

    def __get_keystone_session(self):
        auth = v3.Password(
            username=self.__config.get('openstack', 'username'),
            password=self.__config.get('openstack', 'password'),
            project_name=self.__config.get('openstack', 'project_name'),
            user_domain_name=self.__config.get('openstack',
                                               'user_domain_name'),
            project_domain_name=self.__config.get(
                'openstack', 'project_domain_name'
            ),
            auth_url=self.__config.get('openstack', 'auth_url')
        )

        ks_session = session.Session(auth=auth)

        return ks_session

    def __get_nova_client(self):
        ks_session = self.__get_keystone_session()
        nova_conn = nova_client.Client('2', session=ks_session)
        return nova_conn

    def migrate(self, server_id, new_host):
        server = self.__nova_conn.servers.get(server_id)
        actual_host = server.__getattr__('OS-EXT-SRV-ATTR:host')
        if actual_host == new_host:
            return "Impossible to execute migration to same host"
        else:
            req_migration = server.live_migrate(host=new_host)
            print req_migration

        return "Executing migration of instance %s from %s to %s" % (
            server_id, actual_host, new_host
        )

    def available_hosts(self):
        available_hosts = []
        infra_hosts = self.__config.get('infrastructure', 'hosts').split(',')
        for host in self.__nova_conn.hosts.list():
            if host.host_name in infra_hosts:
                available_hosts.append(host.host_name)

        return available_hosts

    def get_host_instances(self, host):
        instances_ids = []
        opts = {'all_tenants': '1', 'host': host}
        for instance in self.__nova_conn.servers.list(search_opts=opts):
            instances_ids.append(instance.id)
        return instances_ids

    def hosts_free_resources(self, hosts):
        free_usage = {}
        for host in hosts:
            for host_usage in self.__nova_conn.hosts.get(host):
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

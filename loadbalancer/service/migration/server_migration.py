

from novaclient import client as nova_client
from keystoneauth1.identity import v3
from keystoneauth1 import session

import ConfigParser


class MigrateServer:

    def __init__(self):
        config = ConfigParser.RawConfigParser()
        config.read('load_balancer.cfg')
        self.__nova_conn = self.__get_nova_client(config)

    def __get_keystone_session(self, auth_params):
        auth = v3.Password(
            username=auth_params.get('openstack', 'username'),
            password=auth_params.get('openstack', 'password'),
            project_name=auth_params.get('openstack', 'project_name'),
            user_domain_name=auth_params.get('openstack', 'user_domain_name'),
            project_domain_name=auth_params.get(
                'openstack', 'project_domain_name'
            ),
            auth_url=auth_params.get('openstack', 'auth_url')
        )

        ks_session = session.Session(auth=auth)

        return ks_session

    def __get_nova_client(self, auth_params):
        ks_session = self.__get_keystone_session(auth_params)
        nova_conn = nova_client.Client('2', session=ks_session)
        return nova_conn

    def migrate(self, server_id, new_host):
        # TODO allow instance name if possible
        server = self.__nova_conn.servers.get(server_id)
        if server.__getattr__('OS-EXT-SRV-ATTR:host') == new_host:
            return "Impossible to execute migration to same host"
        else:
            req_migration = server.live_migrate(host=new_host,
                                                block_migration=True)
            print req_migration
        return "Executing migration"

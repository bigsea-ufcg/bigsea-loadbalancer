from loadbalancer.service.monasca.manager import MonascaManager
from loadbalancer.service.migration.server_migration import MigrateServer


class HeuristicManager(object):

    def __init__(self):
        super(HeuristicManager, self).__init__()
        self.monasca = MonascaManager()

    def execute_heuristic(self, **kwargs):
        if not kwargs:
            return self.__cpu_optimization()
        else:
            # TODO: improve this without many conditions to select
            # what heuristic use
            if 'heuristic' in kwargs:
                heuristic = kwargs.get('heuristic')
                if heuristic == 'cpu_optimization':
                    return self.__cpu_optimization()
                elif heuristic == 'mem_optimization':
                    return self.__mem_optimization()
                elif heuristic == 'disk_optimization':
                    return self.__disk_optimization()
                elif heuristic == 'net_optimization':
                    return self.__net_optimization()
                else:
                    # TODO: raise another HTTP Status
                    return "Invalid Heuristic"
            else:
                # TODO: raise another HTTP Status
                return "Invalid parameter"

    # TODO: Get hostname information from load_balancer.cfg
    # TODO: Get instances information for all given hosts in load_balancer.cfg
    # using python-novaclient
    def __cpu_optimization(self):
        print "Executing cpu_optimization Heuristic"
        migrator = MigrateServer()

        print migrator.get_hosts_instances(
            migrator.available_hosts()
        )

        # Get Hosts cpu.percent metric (dict {'hostname': last(cpu.percent) }
        # Verify each instance cpu.usage for each host

        # Get instances cpu usage in each host
        response = migrator.migrate(
            'd6f3c158-be48-41c9-9ca8-7ff477ed9bb1', 'c4-compute11'
        )
        # return str(
        #     self.monasca.last_measurement(
        #         'cpu.percent', {'hostname': 'c4-compute11.lsd.ufcg.edu.br'}
        #     )
        # )
        return response

    def __mem_optimization(self):
        print "Executing mem_optimization Heuristic"
        return str(
            self.monasca.last_measurement(
                'cpu.percent', {'hostname': 'c4-compute11.lsd.ufcg.edu.br'}
            )
        )

    def __disk_optimization(self):
        return "Executing disk_optimization Heuristic"

    def __net_optimization(self):
        return "Executing net_optimization Heuristic"

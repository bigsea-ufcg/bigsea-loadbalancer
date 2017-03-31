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
                else:
                    # TODO: raise another HTTP Status
                    return "Invalid Heuristic"
            else:
                # TODO: raise another HTTP Status
                return "Invalid parameter"

    def __cpu_optimization(self):
        print "Executing cpu_optimization Heuristic"
        migrator = MigrateServer()
        hosts = migrator.available_hosts()

        metrics = {}
        for host in hosts:
            hostname = host + '.lsd.ufcg.edu.br'
            metric = self.monasca.last_measurement(
                'cpu.percent', {'hostname': hostname}
            )
            host_instances = migrator.get_host_instances(host)
            instances_info = self.monasca.get_measurements_group(
                'vm.cpu.utilization_norm_perc', 'resource_id',
                hostname, host_instances
            )
            metrics.update({
                host: {'value': metric['value'],
                       'instances': instances_info}
            })

        free_resource_info = migrator.hosts_free_resources(hosts)

        decision = self.__cpu_optimization_decision(metrics,
                                                    free_resource_info)
        print decision

        return str(metrics)

        # Get Hosts cpu.percent metric (dict
        # {'hostname' : {
        #                 'value': cpu.percent,
        #                 'instances': {
        #                                 'id1' : cpu.percent,
        #                                 'id2' : cpu.percent }
        #                 }
        # }
        #
        # Verify each instance cpu.usage for each host

        # Get instances cpu usage in each host
        # response = migrator.migrate(
        #     '7cb820ac-1394-4f3b-bc01-be1f70b6699c', 'c4-compute12'
        # )
        # return "" #response

    def __cpu_optimization_decision(self, metrics, free_resource_info):

        return None

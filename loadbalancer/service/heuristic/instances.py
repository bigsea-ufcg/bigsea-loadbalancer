from loadbalancer.service.heuristic.base import BaseHeuristic


class BalanceInstancesOS(BaseHeuristic):

    def __init__(self, **kwargs):
        print "init Balance Instances"
        self.monasca = kwargs['monasca']
        if kwargs['provider'] == 'OpenStack':
            self.openstack = kwargs['openstack']

    def collect_information(self):
        hosts = self.openstack.available_hosts()

        metrics = {}
        for host in hosts:
            hostname = host + '.lsd.ufcg.edu.br'
            metric = self.monasca.last_measurement(
                'cpu.percent', {'hostname': hostname}
            )

            host_instances = self.openstack.get_host_instances(host)

            instances_info = self.monasca.get_measurements_group(
                'vm.cpu.utilization_norm_perc', 'resource_id',
                hostname, host_instances
            )

            metrics.update({
                host: {'value': metric['value'], 'instances': instances_info}
            })


        resource_info = self.openstack.hosts_resources(hosts)
        print resource_info
        return (metrics, resource_info)

    def decision(self):
        metrics, resource = self.collect_information()
        #hosts_ percentage = self.

        evacuate_host, instances_count = self.__high_utilization_host(metrics)

        num_available_hosts = len(metrics)
        num_instances_host = self.__hosts_instances_count(metrics)
        total_instances = sum(
            len(host['instances']) for host in metrics.values()
        )

        # TODO: Update to a function in other heuristics
        # When considering performance and different sizes of instances
        ideal_number_of_instances = total_instances / num_available_hosts

        migrations = {}

        instances_evacuate = metrics[evacuate_host]['instances']

        while instances_count != ideal_number_of_instances:
            for instance in instances_evacuate:
                host_destiny = self.select_host(num_instances_host,
                                                evacuate_host)
                migrations[instance] = host_destiny
                num_instances_host[host_destiny] += 1
                num_instances_host[evacuate_host] -= 1
                instances_count -= 1
                if instances_count == ideal_number_of_instances:
                    break

        print(migrations)

        # for instance in migrations:
        #     print(self.openstack.live_migration(
        #         instance, migrations[instance]
        #     ))
        return ""

    def __high_utilization_host(self, metrics):
        high_utilization_host = None
        for host in metrics:
            if not high_utilization_host:
                high_utilization_host = host
            else:
                high_utilization = metrics[high_utilization_host]['value']
                if high_utilization >= metrics[host]['value']:
                    pass
                else:
                    high_utilization_host = host
        instances_count = len(metrics[high_utilization_host]['instances'])
        return (high_utilization_host, instances_count)

    def __hosts_instances_count(self, metric):
        hosts_instances = {}
        for host in metric:
            hosts_instances[host] = len(metric[host]['instances'])
        return hosts_instances

    def select_host(self, hosts_instances, ignore_host):
        hosts_instances_local = hosts_instances.copy()
        hosts_instances_local.pop(ignore_host)
        less_instances = None
        for host in hosts_instances_local:
            if not less_instances:
                less_instances = host
            else:
                num_instances = hosts_instances_local[less_instances]
                if num_instances > hosts_instances_local[host]:
                    less_instances = host
        return less_instances

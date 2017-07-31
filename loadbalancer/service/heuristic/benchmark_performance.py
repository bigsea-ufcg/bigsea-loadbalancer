from loadbalancer.service.heuristic.base import BaseHeuristic
from loadbalancer.utils.kvm import RemoteKvm
from loadbalancer.utils.logger import configure_logging, Log

import json
import os.path
import Queue as Q


class SysbenchPerfCPUCap(BaseHeuristic):

    def __init__(self, **kwargs):
        self.logger = Log(
            "SysbenchPerfCPUCap", "heuristic_SysbenchPerfCPUCap.log"
        )
        self.lb_logger = Log("mainHeuristic", "loadbalancer_main.log")
        self.host_logger = Log("hostinfo", "hosts_information.log")
        configure_logging()
        self.monasca = kwargs['monasca']
        self.kvm = RemoteKvm(kwargs['config'])
        if kwargs['provider'] == 'OpenStack':
            self.openstack = kwargs['openstack']
        self.ratio = float(kwargs['config'].get('heuristic', 'cpu_ratio'))
        self.wait_rounds = int(
            kwargs['config'].get('heuristic', 'wait_rounds')
        )
        self.infra_hostnames = kwargs['config'].get(
            'infrastructure', 'hosts'
        ).split(',')
        self.lb_logger.log(
            "ProactiveCPUCap configuration: cpu_ratio=%s | wait_rounds=%s" %
            (str(self.ratio), str(self.wait_rounds))
        )

    def collect_information(self):
        self.logger.log("Start to collect metrics")
        hosts = self.openstack.available_hosts()

        metrics = {}
        for host in hosts:
            self.lb_logger.log(
                "Gathering metrics and information about Host %s" % host
            )
            hostname = [name for name in self.infra_hostnames if
                        host in name]
            hostname = hostname[0]
            host_instances = self.openstack.get_host_instances(host)

            metric = self.monasca.last_measurement(
                'cpu.percent', {'hostname': hostname}
            )
            self.logger.log(
                "Collected cpu.percent metric from host %s" % hostname
            )

            instances_utilization = self.monasca.get_measurements_group(
                'vm.cpu.utilization_norm_perc', 'resource_id',
                hostname, host_instances
            )
            self.logger.log(
                "Collected vm.utilization metric from instances in host %s" %
                hostname
            )

            cpu_cap_percentage = self.kvm.get_percentage_cpu_cap(
                host, host_instances
            )
            self.logger.log(
                "Collected cpu_cap from all instances in host %s" % hostname
            )

            instances_flavor = self.openstack.get_flavor_information(
                host_instances
            )

            instances_metrics, consumption, cap = self._calculate_metrics(
                instances_utilization, cpu_cap_percentage,
                instances_flavor, host_instances
            )

            performance_metric = self.monasca.last_measurement(
                'sysbench.cpu.performance',
                {'hostname': hostname, 'benchmark': 'sysbench',
                 'type': 'CPU', 'threads': '8'}
            )
            self.logger.log(
                "Collected performance metric from host host %s" % hostname
            )
            metrics.update({
                host: {'cpu_perc': metric['value'],
                       'consumption': consumption,
                       'cap': cap,
                       'instances': instances_metrics,
                       'performance_time': performance_metric
                       },
            })

        computes_resources = self.openstack.hosts_resources(hosts)
        self.logger.log("Finished to collect metrics")
        return metrics, computes_resources

    def decision(self):
        metrics, resources = self.collect_information()
        overloaded_hosts = self._get_overloaded_hosts(metrics, resources)
        all_hosts = self.openstack.available_hosts()
        waiting = self._get_waitting_instances()

        if not overloaded_hosts:
            self.logger.log("No hosts overloaded")
            self.lb_logger.log("No hosts overloaded")
            self._write_waitting_instances({}, waiting)
            self._write_migrations({})
        elif set(overloaded_hosts) == set(all_hosts):
            self.logger.log(
                "Overloaded hosts %s are equal to available hosts"
                % overloaded_hosts
            )
            self.logger.log("No migrations can be done")
            self.lb_logger.log(
                "Overloaded hosts %s are equal to available hosts"
                % overloaded_hosts
            )
            self.lb_logger.log("No migrations can be done")
            self._write_waitting_instances({}, waiting)
            self._write_migrations({})
        else:
            self.logger.log("Overloaded hosts %s" % str(overloaded_hosts))
            self.lb_logger.log("Overloaded hosts %s" % str(overloaded_hosts))
            self._define_migrations(
                metrics, resources, overloaded_hosts, waiting
            )

    def _define_migrations(self, metrics, resources, overloaded_hosts,
                           waiting):
        updated_resources = resources.copy()
        waiting = waiting
        migrations = {}
        self.logger.log("Overloaded hosts %s" % str(overloaded_hosts))
        for host in overloaded_hosts:
            self.logger.log("Host: %s" % host)
            host_perf_time = metrics[host]['performance_time']

            better_hosts, worst_hosts = self.get_available_host(metrics, host,
                                                                host_perf_time)

            is_overloaded = self._host_is_loaded(host, updated_resources,
                                                 metrics)

            while is_overloaded:
                self.logger.log("Find %s hosts with better performance" %
                                better_hosts._qsize())
                metrics, migrations, updated_resources = \
                    self.migrate_better_hosts(
                        better_hosts, host, is_overloaded, metrics, migrations,
                        updated_resources, waiting
                    )

                is_overloaded = self._host_is_loaded(
                    host, updated_resources, metrics
                )
                if not is_overloaded:
                    break

                self.logger.log("Find %s hosts with worst performance" %
                                worst_hosts._qsize())
                metrics, migrations, updated_resources = \
                    self.migrate_worst_hosts(
                        host, is_overloaded, metrics, migrations,
                        updated_resources, waiting, worst_hosts
                    )

                is_overloaded = self._host_is_loaded(
                    host, updated_resources, metrics
                )
                if is_overloaded:
                    break

        self.logger.log("Migrations")
        self.logger.log(str(migrations))
        performed_migrations = self.openstack.live_migration(
            migrations)
        self._write_migrations(performed_migrations)
        self._write_waitting_instances(performed_migrations,
                                       waiting)
        self.host_logger.log(
            "----------------------------------------------------------------")
        self.lb_logger.log(
            "----------------------------------------------------------------")

    def migrate_worst_hosts(self, host, is_overloaded, metrics, migrations,
                            updated_resources, waiting, worst_hosts):

        while not worst_hosts.empty():
            new_host = worst_hosts.get()[1]
            self.logger.log("Selected host %s" % new_host)
            if not is_overloaded:
                break

            priority_instances = self._select_low_instance(
                metrics[host]['instances'], waiting
            )
            updated_resources, metrics, migrations = \
                self.reallocate_instances(
                    host, priority_instances, metrics, new_host,
                    updated_resources, migrations
                )
            is_overloaded = self._host_is_loaded(
                host, updated_resources, metrics
            )
        return metrics, migrations, updated_resources

    def migrate_better_hosts(self, better_hosts, host, is_overloaded, metrics,
                             migrations, updated_resources, waiting):
        while not better_hosts.empty():
            new_host = better_hosts.get()[1]
            self.logger.log("Selected host %s" % new_host)
            if not is_overloaded:
                break

            priority_instances = self._select_higher_instances(
                metrics[host]['instances'], waiting
            )
            updated_resources, metrics, migrations = \
                self.reallocate_instances(
                    host, priority_instances, metrics, new_host,
                    updated_resources, migrations
                )
            is_overloaded = self._host_is_loaded(
                host, updated_resources, metrics
            )
        return metrics, migrations, updated_resources

    def reallocate_instances(self, host, priority_instances, metrics, new_host,
                             resources, migrations):
        while not priority_instances.empty():
            instance_id = priority_instances.get()[1]
            self.logger.log("Selected instance %s" % instance_id)
            instance_info = metrics[host]['instances'][instance_id]

            instance_fit = self.instance_fit_host(
                instance_info, new_host, resources, metrics
            )
            if instance_fit:
                self.logger.log("Instance %s will go to host %s" %
                                (instance_id, new_host))

                migrations.update({instance_id: new_host})
                # Update resources
                resources = self._reallocate_resources(
                    resources, host, new_host, instance_info
                )
                # Update metrics
                metrics = self._metrics_update(
                    metrics, host, new_host, instance_id, instance_info
                )

                is_overloaded = self._host_is_loaded(host, resources, metrics)
                if not is_overloaded:
                    self.logger.log(
                        "Host %s is no longer overloaded" % host
                    )
                    break
                else:
                    self.logger.log("Host %s still overloaded" % host)
                    continue
            else:
                self.logger.log("Instance %s doesn't fit in host %s" %
                                (instance_id, new_host))
                continue
        return resources, metrics, migrations

    def _calculate_metrics(self, utilization, cap, flavor, instances):
        metrics = {}
        host_consumption = 0
        host_cap = 0
        self.logger.log(
            "Calculating consumption and used_capacity for each instance"
        )
        for instance_id in instances:
            try:
                used_capacity = flavor[instance_id]['vcpus'] * cap[instance_id]
                consumption = used_capacity * (utilization[instance_id] / 100.)
                host_consumption += consumption
                host_cap += used_capacity
                metrics[instance_id] = {'vcpus': flavor[instance_id]['vcpus'],
                                        'memory': flavor[instance_id]['ram'],
                                        'disk': flavor[instance_id]['disk'],
                                        'cap': cap[instance_id],
                                        'consumption': consumption,
                                        'used_capacity': used_capacity}
                self.logger.log(
                    "%s | utilization: %s | cap: %s | CPU: %s  " %
                    (instance_id, utilization[instance_id], cap[instance_id],
                     flavor[instance_id]['vcpus'])
                )
                self.logger.log(
                    "calculated consumption and used_capacity for instance %s"
                    % instance_id
                )
            except KeyError:
                self.logger.log(
                    "Missing information about instance %s " % instance_id
                )

        return metrics, host_consumption, host_cap

    def _get_overloaded_hosts(self, metrics, resource_info):
        self.logger.log("Looking for overloaded hosts")
        overloaded_hosts = []

        for host in resource_info:
            self.logger.log(host)
            num_cores = resource_info[host]['total']['cpu']
            total_consumption = (
                metrics[host]['consumption'] / float(num_cores)
            )
            total_cap = (
                metrics[host]['cap'] / float(num_cores)
            )
            self.logger.log(
                ("host %s | consp %s | cap %s" %
                 (host, total_consumption, total_cap))
            )

            used = resource_info[host]['used_now']['cpu']
            cpu_perc = metrics[host]['cpu_perc']
            self.host_logger.log(
                "Host %s | CPU %s/%s cores" % (host, used, num_cores)
            )
            self.host_logger.log(
                "Host %s | CPU(%%) =%.2f |TotalConsump=%.2f | TotalCap=%.2f" %
                (host, cpu_perc, total_consumption, total_cap)
            )
            self.host_logger.log(
                "Host %s | %s Virtual Machine(s)\n" %
                (host, len(metrics[host]['instances']))
            )
            if total_consumption > self.ratio and host not in overloaded_hosts:
                overloaded_hosts.append((host, total_cap))
            else:
                if total_cap > self.ratio and host not in overloaded_hosts:
                    overloaded_hosts.append((host, total_cap))
        self.logger.log(str(overloaded_hosts))
        ord_ovld_hosts = [
            e[0] for e in sorted(overloaded_hosts, key=lambda tup: tup[1])
        ]
        self.logger.log(str(ord_ovld_hosts))
        return ord_ovld_hosts

    def _select_low_instance(self, instances_host, waitting_instances):
        instances = list(
            set(instances_host.keys()) - set(waitting_instances))
        priority_instances = Q.PriorityQueue()
        for instance_id in instances:
            consumption = instances_host[instance_id]['consumption']
            priority_instances.put((consumption, instance_id))
        return priority_instances

    def _select_higher_instances(self, instances_host, waiting_instances):
        instances = list(
            set(instances_host.keys()) - set(waiting_instances))
        priority_instances = Q.PriorityQueue()
        for instance_id in instances:
            consumption = instances_host[instance_id]['consumption'] * -1
            priority_instances.put((consumption, instance_id))
        return priority_instances

    def get_available_host(self, metrics, actual_host, performance_value):
        better_hosts = Q.PriorityQueue()
        worst_hosts = Q.PriorityQueue()
        for host in metrics:
            if host == actual_host:
                continue
            else:
                host_performance = metrics[host]['performance_time']
                if host_performance >= performance_value:
                    worst_hosts.put((host_performance, host))
                else:
                    better_hosts.put((host_performance, host))
        return better_hosts, worst_hosts

    def instance_fit_host(self, instance_info, new_host,
                          resource_info, metrics):
        num_cores = resource_info[new_host]['total']['cpu']
        cap_in_use = metrics[new_host]['cap']
        future_total_cap = (
            (cap_in_use + instance_info['used_capacity']) / float(num_cores)
        )
        memory_free = (resource_info[new_host]['total']['memory_mb'] >=
                       resource_info[new_host]['used_now']['memory_mb'] +
                       instance_info['memory'])
        disk_free = (resource_info[new_host]['total']['disk_gb'] >=
                     resource_info[new_host]['used_now']['disk_gb'] +
                     instance_info['disk'])

        if future_total_cap <= self.ratio and memory_free and disk_free:
            return True
        else:
            return False

    def _host_is_loaded(self, host, resource_info, metrics):
        num_cores = resource_info[host]['total']['cpu']
        total_used_cap = (
            metrics[host]['cap'] / float(num_cores)
        )
        if total_used_cap > self.ratio:
            return True
        else:
            return False

    def _reallocate_resources(self, resources, old_host, new_host,
                              instance_info):
        resources[new_host]['used_now']['cpu'] += instance_info['vcpus']
        resources[old_host]['used_now']['cpu'] -= instance_info['vcpus']
        resources[new_host]['used_now']['memory_mb'] += instance_info[
            'memory']
        resources[old_host]['used_now']['memory_mb'] -= instance_info[
            'memory']
        resources[new_host]['used_now']['disk_gb'] += instance_info['disk']
        resources[old_host]['used_now']['disk_gb'] -= instance_info['disk']
        return resources

    def _metrics_update(self, metrics, old_host, new_host, instance_id,
                        instance_info):
        del metrics[old_host]['instances'][instance_id]
        metrics[new_host]['instances'].update({instance_id: instance_info})
        metrics[new_host]['consumption'] += instance_info['consumption']
        metrics[old_host]['consumption'] -= instance_info['consumption']
        metrics[new_host]['cap'] += instance_info['used_capacity']
        metrics[old_host]['cap'] -= instance_info['used_capacity']
        return metrics

    def _get_waitting_instances(self):
        self.logger.log("")
        if os.path.isfile('waitting_instances.json'):
            with open('waitting_instances.json') as json_file:
                return json.load(json_file)
        else:
            return {}

    def _write_waitting_instances(self, migrations, waiting):
        new_waiting = waiting.copy()
        for instance in waiting:
            waiting_rounds = waiting[instance] + 1
            if waiting_rounds >= self.wait_rounds:
                del new_waiting[instance]
            else:
                new_waiting[instance] = waiting_rounds
        for instance in migrations:
            new_waiting[instance] = 0
        with open('waitting_instances.json', 'w') as output:
            json.dump(new_waiting, output)

    def _write_migrations(self, migrations):
        self.logger.log("Writting migrations")
        with open('migrations.json', 'w') as outfile:
            json.dump(migrations, outfile)

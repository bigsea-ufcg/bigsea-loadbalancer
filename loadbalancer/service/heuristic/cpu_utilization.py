from loadbalancer.service.heuristic.base import BaseHeuristic
from loadbalancer.utils.kvm import RemoteKvm
from loadbalancer.utils.logger import configure_logging, Log
from loadbalancer.utils.migration import MigrationUtils as utils

import copy
import Queue as Q


class CPUUtilization(BaseHeuristic):

    def __init__(self, **kwargs):
        self.logger = Log(
            "CPUUtilization", "heuristic_CPUUtilization.log"
        )
        self.lb_logger = Log("mainHeuristic", "loadbalancer_main.log")
        self.host_logger = Log("hostinfo", "hosts_information.log")
        configure_logging()

        self.monasca = kwargs['monasca']
        self.optimizer = kwargs['optimizer']
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
            "CPUUtilization configuration: cpu_ratio=%s | wait_rounds=%s" %
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
            hostname = [name for name in self.infra_hostnames
                        if name.split(".")[0] in host]
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

            instances_flavor = self.openstack.get_flavor_information(
                host_instances
            )

            instances_metrics, consumption, cap = self._calculate_metrics(
                instances_utilization, cpu_cap_percentage,
                instances_flavor, host_instances
            )

            metrics.update({
                host: {'cpu_perc': metric['value'],
                       'consumption': consumption,
                       'cap': cap,
                       'instances': instances_metrics
                       },
            })

        computes_resources = self.openstack.hosts_resources(hosts)
        self.logger.log("Finished to collect metrics")
        return metrics, computes_resources

    def decision(self):
        metrics, resource = self.collect_information()
        self.logger.log("Decision Metrics")
        self.logger.log(str(metrics))
        overloaded_hosts = self._get_overloaded_hosts(metrics, resource)
        all_hosts = self.openstack.available_hosts()
        waiting = utils.get_waiting_instances()

        if not overloaded_hosts:
            self.logger.log("No hosts overloaded")
            self.lb_logger.log("No hosts overloaded")
            utils.write_migrations({})
            utils.write_waiting_instances({}, waiting, self.wait_rounds)
        elif set(overloaded_hosts) == set(all_hosts):
            if self.optimizer:
                params = dict(metrics=metrics, resource_info=resource,
                              openstack=self.openstack, ratio=self.ratio)
                optimizer_decision = self.optimizer.decision(**params)
                if optimizer_decision is not None:
                    return self.decision()
            else:
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
                utils.write_migrations({})
                utils.write_waiting_instances({}, waiting, self.wait_rounds)
        else:
            self.logger.log("Overloaded hosts %s" % str(overloaded_hosts))
            self.lb_logger.log("Overloaded hosts %s" % str(overloaded_hosts))
            self._define_migrations(metrics, resource, overloaded_hosts)

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
                                        'used_capacity': used_capacity }
                self.logger.log(
                    "%s | utilization: %s | cap: %s | CPU: %s  " %
                    (instance_id, utilization[instance_id], cap[instance_id],
                     flavor[instance_id]['vcpus'])
                )
            except KeyError:
                self.logger.log(
                    "Missing information about instance %s " % instance_id
                )
                used_capacity = flavor[instance_id]['vcpus'] * cap[instance_id]
                consumption = used_capacity * 1  # Consider 100% of utilization
                host_consumption += consumption
                host_cap += used_capacity

                metrics[instance_id] = {'vcpus': flavor[instance_id]['vcpus'],
                                        'memory': flavor[instance_id]['ram'],
                                        'disk': flavor[instance_id]['disk'],
                                        'cap': cap[instance_id],
                                        'consumption': consumption,
                                        'used_capacity': used_capacity }
                self.logger.log(
                    "Missing information about instance %s " % instance_id
                )

        return metrics, host_consumption, host_cap

    def _get_overloaded_hosts(self, metrics, resource_info):
        self.logger.log("Looking for overloaded hosts")
        overloaded_hosts = []

        for host in resource_info:
            self.logger.log(host)
            host_cpu_utilization = metrics[host]['cpu_perc']

            self.host_logger.log(
                "Host %s | CPU Utilization %s" % (host, host_cpu_utilization)
            )
            self.host_logger.log(
                "Host %s | %s Virtual Machine(s)\n" % (
                    host, len(metrics[host]['instances'])
                )
            )
            # Adicionar a porcentagem de utilizacao desejada
            if host_cpu_utilization > 70:
                overloaded_hosts.append(host)
        self.logger.log(str(overloaded_hosts))
        return overloaded_hosts

    def _define_migrations(self, metrics, resources, overloaded_hosts):

        original_metrics = copy.deepcopy(metrics)
        self.logger.log("define migrations")
        self.logger.log(str(original_metrics))
        updated_resources = resources.copy()
        waiting = utils.get_waiting_instances()
        migrations = {}
        self.logger.log("Overloaded hosts %s" % str(overloaded_hosts))
        for host in overloaded_hosts:

            self.logger.log("Host: %s" % host)
            hosts_instances = self.get_instances(
                metrics[host]['instances'], waiting
            )

            while not hosts_instances.empty():
                instance_id = hosts_instances.get()[1]
                self.logger.log("Selected instance %s" % instance_id)
                instance_info = metrics[host]['instances'][instance_id]

                other_host_resources = updated_resources.copy()
                del other_host_resources[host]
                new_host = self._get_less_loaded_hosts(
                    other_host_resources, instance_info, metrics
                )

                if new_host is None:
                    self.logger.log(
                        "No host found to migrate instance %s"
                        % instance_id
                    )
                    self.lb_logger.log(
                        "No host found to migrate VM %s from host %s"
                        % (instance_info, host)
                    )
                else:
                    migrations.update({instance_id: new_host})
                    # Update Resources
                    updated_resources = utils.reallocate_resources(
                        updated_resources, host, new_host, instance_info
                    )
                    # Update Metrics
                    metrics = utils.metrics_update(
                        metrics, host, new_host, instance_id, instance_info
                    )

                    self.lb_logger.log(
                        "Migrating VM %s from Host %s to Host %s"
                        % (instance_id, host, new_host)
                    )
                    self.lb_logger.log(
                        "Host %s CPU utilization: %2.f %% | Host %s CPU utilization: %2.f %%"
                        % (host, metrics[host]['cpu_perc'], new_host, metrics[new_host]['cpu_perc'])
                    )


        self.logger.log("Migrations")
        self.logger.log(str(migrations))
        performed_migrations = self.openstack.live_migration(migrations)
        utils.write_migrations(performed_migrations)
        utils.write_waiting_instances(performed_migrations, waiting,
                                      self.wait_rounds)
        self.host_logger.log(
            "----------------------------------------------------------------")
        self.lb_logger.log(
            "----------------------------------------------------------------")

    def get_instances(self, instances_host, waiting_instances):
        instances = list(set(instances_host) - set(waiting_instances))
        instances_queue = Q.PriorityQueue()
        self.lb_logger.log("get_instances")
        for instance_id in instances:
            vcpus = instances_host[instance_id]['vcpus'] * -1
            self.lb_logger.log(instance_id)
            self.lb_logger.log(vcpus)
            instances_queue.put((vcpus, instance_id))
        return instances_queue

    def _get_less_loaded_hosts(self, resource_info, instance_info, metrics):
        selected_host = None
        for host in resource_info:
            memory_free = (resource_info[host]['total']['memory_mb'] >=
                           resource_info[host]['used_now']['memory_mb'] +
                           instance_info['memory'])
            disk_free = (resource_info[host]['total']['disk_gb'] >=
                         resource_info[host]['used_now']['disk_gb'] +
                         instance_info['disk'])
            if memory_free and disk_free:
                if selected_host is None:
                    selected_host = host
                else:
                    continue
        return selected_host

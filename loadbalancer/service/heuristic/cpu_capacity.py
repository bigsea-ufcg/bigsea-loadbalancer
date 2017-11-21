from loadbalancer.service.heuristic.base import BaseHeuristic
from loadbalancer.utils.kvm import RemoteKvm
from loadbalancer.utils.logger import configure_logging, Log
from loadbalancer.utils.migration import MigrationUtils as utils

import copy


class CPUCapAware(BaseHeuristic):

    def __init__(self, **kwargs):
        self.logger = Log("CPUCapAware", "heuristic_CPUCapAware.log")
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
            "CPUCapAware configuration: cpu_ratio=%s | wait_rounds=%s" %
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
            hostname = [name for name in self.infra_hostnames if name in host]
            hostname = hostname[0]
            host_instances = self.openstack.get_host_instances(host)

            metric = self.monasca.last_measurement(
                'cpu.percent', {'hostname': hostname}
            )
            self.host_logger.log("")
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
        metrics, resources = self.collect_information()
        self.logger.log("Metrics")
        self.logger.log(str(metrics))
        self.logger.log("Resource Information")
        self.logger.log(str(resources))
        overloaded_hosts = self._get_overloaded_hosts(metrics, resources)
        waiting = utils.get_waiting_instances()

        if not overloaded_hosts:
            self.logger.log("No hosts overloaded")
            self.lb_logger.log("No hosts overloaded")
            utils.write_migrations({})
            utils.write_waiting_instances({}, waiting, self.wait_rounds)
        elif set(overloaded_hosts) == set(self.openstack.available_hosts()):
            if self.optimizer:
                params = dict(metrics=metrics, resource_info=resources,
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
            self._define_migrations(metrics, resources, overloaded_hosts)

    def _define_migrations(self, metrics, resources, overloaded_hosts):
        original_metrics = copy.deepcopy(metrics)
        updated_resources = resources.copy()
        waiting = utils.get_waiting_instances()
        migrations = {}
        self.logger.log("Overloaded hosts %s" % str(overloaded_hosts))
        self.lb_logger.log("Overloaded hosts %s" % str(overloaded_hosts))
        self.lb_logger.log("Migrations")
        for host in overloaded_hosts:

            ignore_instances = []
            num_instances = len(metrics[host]['instances'])

            while len(ignore_instances) != num_instances:

                instance = self._select_instance(
                    metrics[host]['instances'], ignore_instances,
                    waiting.keys()
                )

                instance_info = metrics[host]['instances'][instance]

                other_hosts_resources = updated_resources.copy()

                del other_hosts_resources[host]

                new_host = self._get_less_loaded_hosts(
                    other_hosts_resources, instance_info, metrics
                )
                if new_host is None:
                    self.logger.log(
                        "No host found to migrate instance %s" % instance
                    )
                    ignore_instances.append(instance)
                    self.lb_logger.log(
                        "No host found to migrate VM %s from host %s" %
                        (instance_info, host)
                    )
                else:
                    migrations.update({instance: new_host})
                    ignore_instances.append(instance)

                    # Update Resources
                    updated_resources = utils.reallocate_resources(
                        updated_resources, host, new_host, instance_info
                    )

                    # Update Metrics
                    metrics = utils.metrics_update(metrics, host, new_host,
                                                   instance, instance_info)

                    self.lb_logger.log(
                        "Migrating VM %s from Host %s to Host %s" %
                        (instance, host, new_host)
                    )

                    if self._host_is_loaded(
                            host, updated_resources, metrics
                    ):
                        continue
                    else:
                        break

            still_overloaded = self._host_is_loaded(
                host, updated_resources, metrics
            )
            self.logger.log(str(still_overloaded))
            if still_overloaded and self.optimizer:
                self.logger.log("Optimizer Service")
                params = dict(metrics=original_metrics,
                              resource_info=resources,
                              openstack=self.openstack, ratio=self.ratio)
                optimizer_decision = self.optimizer.decision(**params)
                if optimizer_decision is not None:
                    return self.decision()
        self.logger.log("Migrations")
        self.logger.log(str(migrations))
        performed_migrations = self.openstack.live_migration(migrations)
        utils.write_migrations(performed_migrations)
        utils.write_waiting_instances(performed_migrations, waiting,
                                      self.wait_rounds)
        self.host_logger.log("-------------------------------------------")
        self.lb_logger.log("---------------------------------------------")

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
                    "Instance %s | Cap= %.2f | Consump = %.2f"
                    % (instance_id, used_capacity, consumption)
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
                "Host %s | CPU(%%)=%.2f |TotalConsump=%.2f | TotalCap=%.2f"
                % (host, cpu_perc, total_consumption, total_cap)
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

    def _select_instance(self, instances_host, ignored_instances,
                         waiting_instances):
        selected = None
        instances = list(set(instances_host.keys()) - set(waiting_instances))
        instances = list(set(instances) - set(ignored_instances))
        for instance_id in instances:
            if instance_id in ignored_instances:
                continue
            else:
                if selected is None:
                    selected = instance_id
                else:
                    consumption = instances_host[instance_id]['consumption']
                    if consumption > instances_host[selected]['consumption']:
                        selected = instance_id
        if selected is not None:
            self.logger.log("Selected instance %s to migrate" % selected)
        else:
            self.logger.log("No instances could be selected do migrate")
        return selected

    def _get_less_loaded_hosts(self, resource_info, instance_info, metrics):
        selected_host = None
        selected_host_cap = None
        for host in resource_info:
            num_cores = resource_info[host]['total']['cpu']
            instance_cap = instance_info['used_capacity']
            cap_in_use = metrics[host]['cap']
            future_total_cap = (
                (cap_in_use + instance_cap) / float(num_cores)
            )

            memory_free = (resource_info[host]['total']['memory_mb'] >=
                           resource_info[host]['used_now']['memory_mb'] +
                           instance_info['memory'])
            disk_free = (resource_info[host]['total']['disk_gb'] >=
                         resource_info[host]['used_now']['disk_gb'] +
                         instance_info['disk'])
            if future_total_cap <= self.ratio and memory_free and disk_free:
                if selected_host is None:
                    selected_host = host
                    selected_host_cap = future_total_cap
                else:
                    if future_total_cap < selected_host_cap:
                        selected_host = host
                        selected_host_cap = future_total_cap
                    else:
                        continue
        return selected_host

    def _host_is_loaded(self, host, resource_info, metrics):
        num_cores = resource_info[host]['total']['cpu']
        total_used_cap = (
            metrics[host]['cap'] / float(num_cores)
        )
        if total_used_cap > self.ratio:
            return True
        else:
            return False

from loadbalancer.service.heuristic.base import BaseHeuristic
from loadbalancer.utils.kvm import RemoteKvm
from loadbalancer.utils.logger import configure_logging, Log

import json
import os.path


class ProActiveCap(BaseHeuristic):

    def __init__(self, **kwargs):
        self.logger = Log("ProActiveCap", "heuristic_ProActiveCap.log")
        configure_logging()
        self.monasca = kwargs['monasca']
        self.kvm = RemoteKvm(kwargs['config'])
        if kwargs['provider'] == 'OpenStack':
            self.openstack = kwargs['openstack']
        self.ratio = float(kwargs['config'].get('heuristic', 'cpu_ratio'))
        self.wait_rounds = int(
            kwargs['config'].get('heuristic', 'wait_rounds')
        )
        self.infra_hostsnames = kwargs['config'].get(
            'infrastructure', 'hosts'
        ).split(',')

    def collect_information(self):
        self.logger.log("Start to collect metrics")
        hosts = self.openstack.available_hosts()

        metrics = {}
        for host in hosts:
            hostname = [name for name in self.infra_hostsnames if host in name]
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

            metrics.update({
                host: {'cpu_perc': metric['value'],
                       'consumption': consumption,
                       'cap': cap,
                       'instances': instances_metrics
                       },
            })

        computes_resources = self.openstack.hosts_resources(hosts)
        self.logger.log("Finished to collect metrics")
        return (metrics, computes_resources)

    def decision(self):
        metrics, resources = self.collect_information()
        self.logger.log("Metrics")
        self.logger.log(str(metrics))
        self.logger.log("Resource Information")
        self.logger.log(str(resources))
        updated_resources = resources.copy()
        hosts = self._get_overloaded_hosts(metrics, resources)
        waitting = self._get_waitting_instances()
        migrations = {}

        if hosts == []:
            self.logger.log("No hosts overloaded")
            self._write_migrations({})
        elif set(hosts) == set(self.openstack.available_hosts()):
            self.logger.log(
                "Overloaded hosts %s are equal to available hosts" % hosts
            )
            self.logger.log("No migrations can be done")
            self._write_migrations({})
        else:
            self.logger.log("Overloaded hosts %s" % str(hosts))

            for host in hosts:

                ignore_instances = []
                num_instances = len(metrics[host]['instances'])

                while(len(ignore_instances) != num_instances):

                    instance = self._select_instance(
                        metrics[host]['instances'], ignore_instances,
                        waitting.keys()
                    )

                    instance_info = metrics[host]['instances'][instance]

                    other_hosts_resources = updated_resources.copy()

                    del other_hosts_resources[host]

                    new_host = self._get_less_loaded_hosts(
                        other_hosts_resources, instance_info
                    )
                    if new_host is None:
                        self.logger.log(
                            "No host found to migrate instance %s" % instance
                        )
                        ignore_instances.append(instance)
                    else:
                        migrations.update({instance: new_host})
                        ignore_instances.append(instance)

                        # Update Resources
                        updated_resources = self._reallocate_resources(
                            updated_resources, host, new_host, instance_info
                        )

                        # Update Metrics
                        metrics = self._metrics_update(metrics, host, new_host,
                                                       instance, instance_info)

                        if self._host_is_loaded(
                            host, updated_resources, metrics
                        ):
                            continue
                        else:
                            break
            self.logger.log("Migrations")
            self.logger.log(str(migrations))
            performed_migrations = self.openstack.live_migration(migrations)
            self._write_migrations(performed_migrations)
            self._write_waitting_instances(performed_migrations, waitting)

    def _calculate_metrics(self, utilization, cap, flavor, instances):
        metrics = {}
        host_consumption = 0
        host_cap = 0
        self.logger.log(
            "Calculating consumption and used_capacity for each instance"
        )
        for instance_id in instances:
            # TODO: update to use utilziation information from monasca
            # utilization[instance_id]
            used_capacity = flavor[instance_id]['vcpus'] * cap[instance_id]
            consumption = used_capacity * 1  # utilization[instance_id]
            host_consumption += consumption
            host_cap += used_capacity
            metrics[instance_id] = {'vcpus': flavor[instance_id]['vcpus'],
                                    'memory': flavor[instance_id]['ram'],
                                    'disk': flavor[instance_id]['disk'],
                                    'cap': cap[instance_id],
                                    'consumption': consumption,
                                    'used_capacity': used_capacity}
        return metrics, host_consumption, host_cap

    def _get_overloaded_hosts(self, metrics, resource_info):
        overloaded_hosts = []
        for host in resource_info:
            num_cores = resource_info[host]['total']['cpu']
            total_consumption = (
                metrics[host]['consumption'] / float(num_cores)
            )
            total_cap = (
                metrics[host]['cap'] / float(num_cores)
            )
            if total_consumption > self.ratio:
                overloaded_hosts.append((host, total_cap))
            if total_cap > self.ratio and host not in overloaded_hosts:
                overloaded_hosts.append((host, total_cap))
        ord_ovld_hosts = [
            e[0] for e in sorted(overloaded_hosts, key=lambda tup: tup[1])
        ]
        return ord_ovld_hosts

    def _select_instance(self, instances_host, ignored_instances,
                         waitting_instances):
        print instances_host
        selected = None
        instances = list(set(instances_host.keys()) - set(waitting_instances))
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

    def _get_less_loaded_hosts(self, resource_info, instance_info):
        selected_host = None
        selected_host_cap = None
        for host in resource_info:
            num_cores = resource_info[host]['total']['cpu']
            cores_in_use = resource_info[host]['used_now']['cpu']
            future_total_cap = (
                (cores_in_use + instance_info['vcpus']) / float(num_cores)
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
            metrics[host]['consumption'] / float(num_cores)
        )
        if total_used_cap > self.ratio:
            return True
        else:
            return False

    def _reallocate_resources(self, resources, old_host, new_host,
                              instance_info):
        resources[new_host]['used_now']['cpu'] += instance_info['vcpus']
        resources[old_host]['used_now']['cpu'] -= instance_info['vcpus']
        resources[new_host]['used_now']['memory_mb'] += instance_info['memory']
        resources[old_host]['used_now']['memory_mb'] -= instance_info['memory']
        resources[new_host]['used_now']['disk_gb'] += instance_info['disk']
        resources[old_host]['used_now']['disk_gb'] -= instance_info['disk']
        return resources

    def _metrics_update(self, metrics, old_host, new_host, instance_id,
                        instance_info):
        del metrics[old_host]['instances'][instance_id]
        metrics[new_host]['instances'].update({instance_id: instance_info})
        metrics[new_host]['consumption'] += instance_info['consumption']
        metrics[old_host]['consumption'] -= instance_info['consumption']
        return metrics

    def _get_latest_migrations(self):
        self.logger.log("Reading latest migrations")
        if os.path.isfile('migrations.json'):
            with open('migrations.json') as json_file:
                return json.load(json_file)
        else:
            return {}

    def _get_waitting_instances(self):
        self.logger.log("")
        if os.path.isfile('waitting_instances.json'):
            with open('waitting_instances.json') as json_file:
                return json.load(json_file)
        else:
            return {}

    def _write_waitting_instances(self, migrations, waitting):
        new_waitting = waitting.copy()
        for instance in waitting:
            waitting_rounds = waitting[instance] + 1
            if waitting_rounds >= self.wait_rounds:
                del new_waitting[instance]
            else:
                new_waitting[instance] = waitting_rounds
        for instance in migrations:
            new_waitting[instance] = 0
        with open('waitting_instances.json', 'wa') as output:
            json.dump(new_waitting, output)

    def _write_migrations(self, migrations):
        self.logger.log("Writting migrations")
        with open('migrations.json', 'w') as outfile:
            json.dump(migrations, outfile)

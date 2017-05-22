from loadbalancer.service.heuristic.base import BaseHeuristic
from loadbalancer.utils.kvm import RemoteKvm
from loadbalancer.utils.logger import configure_logging, Log


class ProActiveCap(BaseHeuristic):

    def __init__(self, **kwargs):
        self.logger = Log("ProActiveCap", "heuristic_ProActiveCap.log")
        configure_logging()
        self.monasca = kwargs['monasca']
        self.kvm = RemoteKvm(kwargs['config'])
        if kwargs['provider'] == 'OpenStack':
            self.openstack = kwargs['openstack']
        self.ratio = 0.9 #Add as parameter

    def collect_information(self):
        self.logger.log("Start to collect metrics")
        hosts = self.openstack.available_hosts()

        metrics = {}
        for host in hosts:
            hostname = host + '.lsd.ufcg.edu.br'
            host_instances = self.openstack.get_host_instances(host)

            metric = self.monasca.last_measurement(
                'cpu.percent', {'hostname': hostname}
            )
            self.logger.log("Collected cpu.percent metric from host %s" % hostname)

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
            self.logger.log("Collected cpu_cap from all instances in host %s" %
                    hostname)

            instances_flavor = self.openstack.get_flavor_information(
                host_instances
            )

            instances_metrics, host_used_cap = self._calculate_metrics(
                instances_utilization, cpu_cap_percentage,
                instances_flavor, host_instances
            )

            metrics.update({
                host: {'cpu_perc': metric['value'],
                       'cap': host_used_cap,
                       'instances': instances_metrics
                       },
            })

        computes_resources = self.openstack.hosts_resources(hosts)
        self.logger.log("Finished to collect metrics")
        return (metrics, computes_resources)

    def decision(self):
        metrics, resources = self.collect_information()

        print metrics
        print "==============="
        print resources
        print "###########################################"
        updated_resources = resources.copy()
        hosts = self._get_overloaded_hosts(metrics, resources)

        if hosts == []:
            # No hosts overloaded
            print "No hosts overloaded"
            pass
        else:
            migrations = {}
            for host in hosts:
                ignore_instances = []
                num_instances = len(metrics[host]['instances'])
                while(len(ignore_instances) != num_instances):
                    instance = self._select_instance(
                        metrics[host]['instances'], ignore_instances
                    )
                    instance_info = metrics[host]['instances'][instance]
                    vcpus = instance_info['vcpus']

                    other_hosts_resources = updated_resources.copy()
                    del other_hosts_resources[host]
                    new_host = self._get_less_loaded_hosts(
                        other_hosts_resources, vcpus
                    )
                    print new_host
                    if new_host is None:
                        ignore_instances.append(instance)
                    else:
                        migrations.update({instance: new_host})
                        print migrations
                        ignore_instances.append(instance)

                        # Update Resources
                        updated_resources[new_host]['used_now']['cpu'] += vcpus
                        updated_resources[host]['used_now']['cpu'] -= vcpus
                        # Add update for disk_gb and memory_mb

                        # Update Metrics
                        del metrics[host]['instances'][instance]
                        metrics[new_host]['instances'].update({
                            instance: instance_info
                        })

                        metrics[new_host]['cap'] += (
                            instance_info['used_capacity']
                        )
                        metrics[host]['cap'] -= instance_info['used_capacity']

                        if self._host_is_loaded(
                                host, updated_resources, metrics
                        ):
                            continue
                        else:
                            break
            print "Execute migrations"
            self.openstack.live_migration(migrations)

    def _calculate_metrics(self, utilization, cap, flavor, instances):
        metrics = {}
        host_used_cap = 0
        self.logger.log(
            "Calculating consumption and used_capacity for each instance"
        )
        for instance_id in instances:
            # TODO: update to use utilziation information from monasca
            # utilization[instance_id]
            used_capacity = flavor[instance_id]['vcpus'] * cap[instance_id]
            host_used_cap += used_capacity
            metrics[instance_id] = {'vcpus': flavor[instance_id]['vcpus'],
                                    'cap': cap[instance_id],
                                    'consumption': used_capacity * 1,
                                    'used_capacity': used_capacity}
        return metrics, host_used_cap

    def _get_overloaded_hosts(self, metrics, resource_info):
        overloaded_hosts = []
        for host in resource_info:
            num_cores = resource_info[host]['total']['cpu']
            total_used_cap = (
                metrics[host]['cap'] / float(num_cores)
            )
            print "get overloaded host"
            print total_used_cap
            print self.ratio
            if total_used_cap > self.ratio:
                overloaded_hosts.append(host)
        return overloaded_hosts

    def _select_instance(self, instances, ignore_instances):
        selected = None
        for instance_id in instances:
            if instance_id in ignore_instances:
                continue
            else:
                if selected is None:
                    selected = instance_id
                else:
                    if instances[instance_id] > instances[selected]:
                        selected = instance_id
        return selected

    def _get_less_loaded_hosts(self, resource_info, vcpus):
        # update to recive all flavor information and validate that the host
        # can recive the instance
        selected_host = None
        selected_host_cap = None
        for host in resource_info:
            num_cores = resource_info[host]['total']['cpu']
            cores_in_use = resource_info[host]['used_now']['cpu']
            future_total_cap = (
                (cores_in_use + vcpus) / float(num_cores)
            )
            if future_total_cap < self.ratio:
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

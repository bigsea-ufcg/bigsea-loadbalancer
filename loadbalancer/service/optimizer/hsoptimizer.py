from loadbalancer.service.optimizer.base import BaseOptimizer
from loadbalancer.utils.logger import configure_logging, Log

import json
import requests
import Queue as Q


class HSOptimizer(BaseOptimizer):

    def __init__(self, **kwargs):
        self.logger = Log(
            "HSOptimizer", "hsoptimizer.log"
        )
        configure_logging()
        self.request_url = kwargs['config'].get('optimizer', 'request_url')
        self.params = eval(kwargs['config'].get('optimizer', 'request_params'))
        self.request_type = kwargs['config'].get('optimizer', 'request_type')

    def request_instances(self):
        self.logger.log("Doing request to url: %s" % self.request_url)
        r = requests.request(self.request_type, self.request_url,
                             headers={'Content-Type': 'application/json'},
                             data=json.dumps(self.params))
        if r.content == 'No instance available for deleting':
            self.logger.log(r.content)
            return {}
        else:
            self.logger.log(str(json.loads(r.content)))
            return json.loads(r.content)

    def decision(self, **kwargs):

        cluster_instances = self.request_instances()
        kill_instances = []
        print cluster_instances
        if cluster_instances:
            resource_info = kwargs['resource_info']
            ratio = kwargs['ratio']
            used_cpu, limit_cpu = self.calculate_resources(
                resource_info, ratio
            )
            self.logger.log("Limit CPU %s" % str(limit_cpu))
            self.logger.log("Used CPU %s" % str(used_cpu))
            metrics = kwargs['metrics']
            openstack = kwargs['openstack']
            killable_instances = self.opportunistic_instances(
                cluster_instances, openstack, metrics
            )
            overloaded = used_cpu > limit_cpu

            if killable_instances.empty():
                self.logger.log("No instance to delete")
                return None

            while not (killable_instances.empty()):
                instance = killable_instances.get()
                removed_cpus = instance[0]
                instance_id = instance[1]
                kill_instances.append(instance_id)
                self.logger.log("Selected instance %s" % instance_id)
                self.logger.log("Removed cpus %s" % str(removed_cpus))
                used_cpu += removed_cpus
                overloaded = limit_cpu <= used_cpu
                self.logger.log(str(used_cpu))
                self.logger.log("overloaded: %s" % str(overloaded))
                if used_cpu <= limit_cpu:
                    break

            self.logger.log("Deleting all selected instances")
            self.logger.log(str(kill_instances))
            openstack.delete_instances(kill_instances)

            if overloaded:
                self.logger.log("General threshold above the limit")
                return False
            else:
                self.logger.log("General threshold below the limit")
                return True

        else:
            self.logger.log("No clusters")
            return None

    def calculate_resources(self, resource_info, ratio):
        total_cpu = 0
        used_cpu = 0
        for host in resource_info:
            total_cpu += resource_info[host]['total']['cpu']
            used_cpu += resource_info[host]['used_now']['cpu']
        return used_cpu, total_cpu * ratio

    def opportunistic_instances(self, cluster_info, openstack, metrics):
        self.logger.log("Getting opportunistic instances")
        opportunistic_instances = Q.PriorityQueue()
        for cluster in cluster_info:
            priority = self.get_higher_priority(cluster_info[cluster])
            if priority is None:
                continue
            else:
                self.logger.log("Cluster %s" % cluster)
                for instance_id in cluster_info[cluster][priority]:
                    host = openstack.get_instance_host(instance_id)
                    self.logger.log("Host: %s" % host)
                    self.logger.log(str(metrics[host]))
                    self.logger.log(str(metrics[host]['instances']))
                    instance_metrics = metrics[host]['instances'][instance_id]
                    self.logger.log("%s" % str(instance_metrics))
                    cpus = instance_metrics['vcpus'] * -1
                    self.logger.log("%s" % str(cpus))
                    self.logger.log("Optortunistic instance: %s" % instance_id)
                    opportunistic_instances.put((cpus, instance_id))
        return opportunistic_instances

    def get_higher_priority(self, cluster_info):
        priority = None
        cluster = cluster_info.copy()
        while priority is None:
            try:
                priority = max(cluster.keys())
            except ValueError:
                break
        return priority

import os.path
import json


class MigrationUtils:

    @staticmethod
    def reallocate_resources(resources, old_host, new_host, instance_info):
        resources[new_host]['used_now']['cpu'] += instance_info['vcpus']
        resources[old_host]['used_now']['cpu'] -= instance_info['vcpus']
        resources[new_host]['used_now']['memory_mb'] += instance_info['memory']
        resources[old_host]['used_now']['memory_mb'] -= instance_info['memory']
        resources[new_host]['used_now']['disk_gb'] += instance_info['disk']
        resources[old_host]['used_now']['disk_gb'] -= instance_info['disk']
        return resources

    @staticmethod
    def metrics_update(metrics, old_host, new_host, instance_id,
                       instance_info):
        del metrics[old_host]['instances'][instance_id]
        metrics[new_host]['instances'].update({instance_id: instance_info})
        metrics[new_host]['consumption'] += instance_info['consumption']
        metrics[old_host]['consumption'] -= instance_info['consumption']
        metrics[new_host]['cap'] += instance_info['used_capacity']
        metrics[old_host]['cap'] -= instance_info['used_capacity']
        return metrics

    @staticmethod
    def get_waiting_instances():
        if os.path.isfile('waiting_instances.json'):
            with open('waiting_instances.json') as json_file:
                return json.load(json_file)
        else:
            return {}

    @staticmethod
    def write_waiting_instances(migrations, waiting, wait_rounds):
        new_waiting = waiting.copy()
        for instance in waiting:
            waiting_rounds = waiting[instance] + 1
            if waiting_rounds >= wait_rounds:
                del new_waiting[instance]
            else:
                new_waiting[instance] = waiting_rounds
        for instance in migrations:
            new_waiting[instance] = 0
        with open('waiting_instances.json', 'w') as output:
            json.dump(new_waiting, output)

    @staticmethod
    def write_migrations(migrations):
        with open('migrations.json', 'w') as outfile:
            json.dump(migrations, outfile)

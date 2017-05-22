from loadbalancer.utils.logger import configure_logging, Log
from monascaclient import client as monclient, ksclient

import monascaclient.exc as exc


class MonascaManager:

    def __init__(self, configuration):
        self.configuration = configuration
        self.logger = Log("Monasca", "monasca.log")
        configure_logging()

    def get_measurements(self, metric_name, dimensions,
                         start_time='2014-01-01T00:00:00Z'):
        measurements = []
        try:
            monasca_client = self.__get_monasca_client()
            dimensions = dimensions
            measurements = monasca_client.metrics.list_measurements(
                name=metric_name, dimensions=dimensions,
                start_time=start_time, debug=False)
        except exc.HTTPException as httpex:
            print httpex.message
        except Exception as ex:
            print ex.message
        if len(measurements) > 0:
            return measurements[0]['measurements']
        else:
            return None

    def last_measurement(self, name, dimensions):
        self.logger.log(
            "Get last measurement for metric %s with dimensions %s" %
            (name, str(dimensions))
        )
        response = dimensions.copy()
        response['metric'] = name
        if self.get_measurements(name, dimensions) is None:
            response['timestamp'] = None
            response['value'] = None
            return response
        else:
            measurement = self.get_measurements(name, dimensions)[-1]
            response['timestamp'] = measurement[0]
            response['value'] = measurement[1]
            return response

    def get_measurements_group(self, metric_name,
                               dimension_name, hostname, dimension_values):
        group_measurement = {}
        for element in dimension_values:
            dimension = {dimension_name: element, 'hostname': hostname}
            value = self.last_measurement(
                'vm.cpu.utilization_norm_perc', dimension)['value']
            if value is not None:
                group_measurement[element] = value

        return group_measurement

    def __get_monasca_client(self):
        # Keystone Client
        ks = ksclient.KSClient(
            auth_url=self.configuration.get('monitoring', 'auth_url'),
            username=self.configuration.get('monitoring', 'username'),
            password=self.configuration.get('monitoring', 'password'),
            project_name=self.configuration.get('monitoring', 'project_name'),
        )

        # Monasca Client
        monasca_client = monclient.Client(
            self.configuration.get('monitoring', 'monasca_api_version'),
            ks.monasca_url, token=ks.token,
            debug=False
        )
        self.logger.log("Get Monasca Client")
        return monasca_client

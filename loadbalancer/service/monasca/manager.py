import monascaclient.exc as exc
import ConfigParser

from monascaclient import client as monclient, ksclient


class MonascaManager:

    def __init__(self):
        # Note: Maybe we can figure out another way to not read the configuration again here
        config = ConfigParser.RawConfigParser()
        config.read('load_balancer.cfg')

        self.monasca_username = config.get('monitoring','username')
        self.monasca_password = config.get('monitoring', 'password')
        self.monasca_auth_url = config.get('monitoring', 'auth_url')
        self.monasca_project_name = config.get('monitoring', 'project_name')
        self.monasca_api_version = config.get('monitoring', 'monasca_api_version')

        self._get_monasca_client()

    def get_measurements(self, metric_name, dimensions, start_time='2014-01-01T00:00:00Z'):
        measurements = []
        try:
            monasca_client = self._get_monasca_client()
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

    def first_measurement(self, name, dimensions):
        return [None, None, None] if self.get_measurements(name, dimensions) is None \
            else self.get_measurements(name, dimensions)[0]

    def last_measurement(self, name, dimensions):
        return [None, None, None] if self.get_measurements(name, dimensions) is None \
            else self.get_measurements(name, dimensions)[-1]

    def _get_monasca_client(self):

        # Authenticate to Keystone
        ks = ksclient.KSClient(
            auth_url=self.monasca_auth_url,
            username=self.monasca_username,
            password=self.monasca_password,
            project_name=self.monasca_project_name,
            debug=False
        )

        # Monasca Client
        monasca_client = monclient.Client(self.monasca_api_version, ks.monasca_url,
                                          token=ks.token,
                                          debug=False)

        return monasca_client
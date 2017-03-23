from loadbalancer.conductor import manager


class LocalApi(object):

    def __init__(self):
        self._manager = manager.ConductorManager()

    def migration(self, **kwargs):
        return self._manager.migration(**kwargs)

from loadbalancer.service.heuristic.manager import HeuristicManager


class ConductorManager(object):

    def __init__(self):
        super(ConductorManager, self).__init__()
        self.heuristic = HeuristicManager()

    def migration(self,**kwargs):
        return self.heuristic.execute_heuristic(**kwargs)

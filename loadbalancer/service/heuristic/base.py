import abc
import six


@six.add_metaclass(abc.ABCMeta)
class BaseHeuristic(object):

    @abc.abstractmethod
    def collect_information(self):
        pass

    @abc.abstractmethod
    def decision(self):
        pass

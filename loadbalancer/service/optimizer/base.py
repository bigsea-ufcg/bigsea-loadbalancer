import abc
import six


@six.add_metaclass(abc.ABCMeta)
class BaseOptimizer(object):

    @abc.abstractmethod
    def request_instances(self):
        pass

    @abc.abstractmethod
    def decision(self, **kwargs):
        pass

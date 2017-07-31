import sys

from loadbalancer.openstack.connector import OpenStackConnector
from loadbalancer.utils.monitoring import MonascaManager
from loadbalancer.utils.logger import configure_logging, Log
from loadbalancer.utils import validation


import argparse
import ConfigParser
import time


def command_line_parser():
    parser = argparse.ArgumentParser(
        prog='python loadbalancer/cli/main.py',
        description='Monitoring Host Daemon'
    )
    parser.add_argument(
        '-conf', '--configuration',
        help='Configuration File with all information necessary to run the \
        loadbalancer. If not used will look for load_balancer.cfg in the root \
        directory',
        required=False
    )
    return parser


def get_heuristic_class(module, class_name):
    heuristic_module = ("loadbalancer.service.heuristic." +
                        module + "." + class_name)

    parts = heuristic_module.split('.')
    module = ".".join(parts[:-1])
    module_import = None
    try:
        module_import = __import__(module)
    except Exception as e:
        print(e.message)

    for comp in parts[1:]:
        try:
            module_import = getattr(module_import, comp)
        except Exception as e:
            print(e.message)

    return module_import


def main():

    try:
        logger = Log("main", "loadbalancer_main.log")
        host_logger = Log("mainhostinfo", "hosts_information.log")
        configure_logging()
        cmd = command_line_parser()
        args = validation.cmd(cmd.parse_args())
        logger.log("Validating command line arguments")

        config = ConfigParser.RawConfigParser()
        if args.configuration:
            config.read(args.configuration)
        else:
            config.read('load_balancer.cfg')
        logger.log("Reading configuration file")

        kwargs = {'monasca': MonascaManager(config), 'config': config}

        iaas_provider = config.get('infrastructure', 'provider')
        if iaas_provider == 'OpenStack':
            kwargs['provider'] = iaas_provider
            kwargs['openstack'] = OpenStackConnector(config)
            logger.log("Identified OpenStack as IaaS provider")
            logger.log("Creating OpenStack Connector")

        logger.log("Extracting Heuristic module and class")
        heuristic_period = float(config.get('heuristic', 'period'))
        heuristic_module = config.get('heuristic', 'module')
        heuristic_name = config.get('heuristic', 'class')
        heuristic = get_heuristic_class(heuristic_module, heuristic_name)
        logger.log("Loading Heuristic %s from module %s" %
                   (heuristic_name, heuristic_module))
        heuristic_instance = heuristic(**kwargs)
        logger.log("Successfully created %s Heuristic" % heuristic_name)

        aux = 1
        while True:
            host_logger.log("Host Usage (Load Balancer execution #%s)\n" % aux)
            logger.log("Heuristic %s making decision" % heuristic_name)
            heuristic_instance.decision()
            logger.log("Sleeping for %s seconds" % heuristic_period)
            time.sleep(heuristic_period)
            aux += 1

    except Exception as e:
        print e
        print(e.message)
        sys.exit(2)


if __name__ == '__main__':
    main()

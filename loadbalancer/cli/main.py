import sys

from loadbalancer.openstack.connector import OpenStackConnector
from loadbalancer.openstack.manager import MonascaManager
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
        cmd = command_line_parser()
        args = validation.cmd(cmd.parse_args())

        config = ConfigParser.RawConfigParser()
        if args.configuration:
            config.read(args.configuration)
        else:
            config.read('load_balancer.cfg')

        validation.configuration_file(config)

        os_connector = OpenStackConnector(config)
        monasca = MonascaManager(config)
        heuristic_module = config.get('heuristic', 'module')
        heuristic_name = config.get('heuristic', 'class')

        heuristic = get_heuristic_class(heuristic_module, heuristic_name)
        heuristic_instance = heuristic(os_connector, monasca)
        while True:
            heuristic_instance.execute()
            time.sleep(1800)

    except Exception as e:
        print(e.message)
        sys.exit(2)


if __name__ == '__main__':
    main()

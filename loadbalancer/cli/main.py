
from loadbalancer.cli import *

import ConfigParser

CONFIG = ConfigParser.RawConfigParser()
CONFIG.read("load_balancer.cfg")


host_address = CONFIG.get('loadbalancer','host_address')
host_port = int(CONFIG.get('loadbalancer','host_port'))
use_debug = CONFIG.get('loadbalancer','use_debug')

main(host_address,host_port,use_debug)


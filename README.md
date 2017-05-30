BigSea WP3 - LoadBalancer
=========================

#### Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
    - [Example of configuration file](#example-of-configuration-file)
- [Heuristics](#heuristics)
    - [Creating a Heuristic](#creating-a-heuristic)
- [Running the LoadBalancer](#running-the-loadbalancer)



## Overview

The Load Balancer service is responsible to manage a specific subset off hosts and decide the most effective placement of instances based on a given heuristic according to the information in the configuration file.

## Heuristics

The heuristics are responsible to periodically decide the most effective placement of instances in the hosts. You can write your own heristics, just follow the steps in [Creating a Heuristic](#creating-a-heuristic)
Below we list all available heuristics that we have in our repository.


##### List of Available Heuristics

- [ProActiveCap](loadbalancer/service/heuristic/doc/cpu_capacity.md)


#### Creating a Heuristic

    1. Create a python module file in `loadbalancer/servie/heuristic` directory
    2. In the module file create a class that inherits `BaseHeuristic` class from
        `loadbalancer/servie/heuristic/base.py`
    3. You must override collect_information and execute methods in your class.

**Note:** Remember to update your configuration file with the heuristic you want to use.

## Installation

#### Steps

    $ git clone https://github.com/bigsea-ufcg/bigsea-loadbalancer.git
    $ cd bigsea-loadbalancer/
    $ pip install -r requirements.txt


## Configuration

A configuration file is required to run the loadbalancer. You can find a template in the main directory called
`loadbalancer.cfg.template`, rename the template to `loadbalancer.cfg` or any other name you want.
Make sure you have fill up all fields before run.

#### Create your configuration file

    $ mv loadbalancer.cfg.tempalte configuration.cfg
    $ mv loadbalancer.cfg.tempalte loadbalancer.cfg

#### Example of configuration file

`loadbalancer.cfg.template`


```
[monitoring]
username=<@username>
password=<@password>
project_name=<@project_name>
auth_url=<@auth_url>
monasca_api_version=v2_0

[heuristic]
# The filename for the module that is located in /loadbalancer/service/heuristic/
# without .py extension
module=<module_name>
# The class name that is inside the given module, this class should implement BasicHeuristic
class=<class_name>
#Number of seconds before execute the heuristic again
period=<value>

[infrastructure]
# The user that have access to each host
user=<username>
#List of full hostnames of servers that the loadbalancer will manage (separated by comma).
#e.g compute1.mylab.edu.br
hosts=<host>,<host2>
#The key used to access the hosts
key=<key_path>
#The type of IaaS provider on your infrastructure e.g OpenStack, OpenNebula
provider=<provider_name>

[openstack]
username=<@username>
password=<@password>
user_domain_name=<@user_domain_name>
project_name=<@project_name>
project_domain_name=<@project_domain_name>
auth_url=<@auth_url>
```

## Running the LoadBalancer

    $ export PYTHONPATH=$PYTHONPATH":/path/to/bigsea-loadbalancer"
    $ cd loadbalancer/

##### Default configuration file

    $ python loadbalancer/cli/main.py

##### Especific configuration file

    $ python loadbalancer/cli/main.py -conf my_configuration.cfg

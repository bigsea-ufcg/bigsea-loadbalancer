BigSea WP3 - LoadBalancer
=========================

#### Table of Contents

- [Overview](#overview)
    - [Architecture](#architecture)
- [Heuristics](#heuristics)
    - [Creating a Heuristic](#creating-a-heuristic)
- [Installation](#installation)
- [Configuration](#configuration)
    - [Example of configuration file](#example-of-configuration-file)
- [Running the LoadBalancer](#running-the-loadbalancer)



Overview
--------

The Load Balancer service is responsible for managing a specific subset of hosts, where VM's are running applications,
and reallocate VM's that are on overloaded hosts, the decision is based on the heuristic that is in the configuration file.


### Architecture

The LoadBalancer need to access to Nova and Monasca in your Cloud Infrastructure, sometime it may require ssh access to hosts to perform actions
(e.g. discover VM's CPU capacity)

<Image>


### Dependencies

To have your Load Balancer working properly you need to ensure that it has access to following components in your Infrastructure:

* OpenStack Compute Service - *Nova* (with admin privileges)
* OpenStack Monitoring Service - *Monasca*
* Infrastructure Hosts (KVM Hypervisor)


Heuristics
----------

The heuristics are responsible to periodically verify wich hosts are overloaded, taking actions to reallocate VM's of these hosts
to others, trying to make them less overloaded than before when possible.
You can write your own heristics, just follow the steps in [Creating a Heuristic](#creating-a-heuristic)
Below we list all available heuristics that we have in our repository.


#### List of Available Heuristics

- [ProActiveCap](loadbalancer/service/heuristic/doc/cpu_capacity.md)


### Creating a Heuristic

1. Create a python module file in `loadbalancer/servie/heuristic` directory
2. In the module file create a class that inherits `BaseHeuristic` class from `loadbalancer/servie/heuristic/base.py`
3. You must override collect_information and execute methods in your class.

**Note:** Remember to update the `heuristic` section in your configuration file with the heuristic you want to use.


Installation
------------

### Steps

    $ git clone https://github.com/bigsea-ufcg/bigsea-loadbalancer.git
    $ cd bigsea-loadbalancer/
    $ pip install -r requirements.txt


Configuration
-------------

A configuration file is required to run the loadbalancer. You can find a template in the main directory called
`loadbalancer.cfg.template`, rename the template to `loadbalancer.cfg` or any other name you want.
Make sure you have fill up all fields before run.


### Example of configuration file

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

Limitations
-----------

* Only support OpenStack Infrastructure
* Nova Live Migrations considers only *shared storage-based live migrations* (We don't take in consideration the migration cost)


Running the LoadBalancer
------------------------

    $ export PYTHONPATH=$PYTHONPATH":/path/to/bigsea-loadbalancer"
    $ cd loadbalancer/

#### Default configuration file

    $ python loadbalancer/cli/main.py

#### Especific configuration file

    $ python loadbalancer/cli/main.py -conf load_balancer.cfg

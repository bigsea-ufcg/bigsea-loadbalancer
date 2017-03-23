BigSea WP3 - LoadBalancer
=========================

#### Table of Contents

- [Overview](#overview)
    - [LB API](#loadbalancer-api)
- [Installation](#installation)
- [Configuration](#configuration)
    - [Example of configuration file](#example-of-configuration-file)
- [Running the LoadBalancer](#running)


## Overview

...

#### LB API

| HTTP Method | Action | URI | Parameters |
|:------------:|:-------------:|:-------------:|:-------------|
| GET | Request a migration to balance servers using the default heuristic or a given one | http://<host_address>:<host_port>/migration/cpu_usage | Optional: heuristic=name |




## Installation

**Steps**

    $ git clone https://github.com/bigsea-ufcg/bigsea-loadbalancer.git
    $ cd loadbalancer/
    $ pip install -r requirements.txt
    $ python steup.py install


## Configuration

A configuration file is required to run the loadbalancer. You can find a template in the main directory called
`loadbalancer.cfg.template`, rename the template to `loadbalancer.cfg`and fill up all fields before run.

#### Example of configuration file

`loadbalancer.cfg.template`

```
[openstack]
username=
password=
user_domain_name=
project_name=
project_domain_name=
auth_url=


[monitoring]
username=
password=
project_name=
auth_url=
monasca_api_version=


[infrastructure]
servers=<>
#List of hostnames or ips of servers that the loadbalancer will manage (separated by comma).


[loadbalancer]
host_address=0.0.0.0
host_port=2700
use_debug=False
```


## Running the LoadBalancer

    $ cd loadbalancer/
    $ python loadbalancer/cli/main.py


from loadbalancer import conductor as c
from loadbalancer.utils.logger import *

conductor = c.API
LOG = Log("Service-V1-API", "service_v1api.log")

def service_api_migration(**kwargs):
    migration_response = conductor.migration(**kwargs)
    return migration_response

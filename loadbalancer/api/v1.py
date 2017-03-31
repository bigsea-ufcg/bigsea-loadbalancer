from loadbalancer.service.api import v1 as api_v1
# from loadbalancer.service import validation as validator
import loadbalancer.utils.api as api_util

rest_api = api_util.Rest('v1', __name__)


@rest_api.get('/migration')
def migration():
    result = api_v1.service_api_migration(
        **api_util.get_request_args().to_dict()
    )
    print result
    return result

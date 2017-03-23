from loadbalancer.conductor import api as conductor_api


def Api(**kwargs):
    api = conductor_api.LocalApi

    return api(**kwargs)

API = Api()
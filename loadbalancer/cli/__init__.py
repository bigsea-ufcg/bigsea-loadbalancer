from flask import Flask
from loadbalancer.api.v1 import rest_api

def main(host_address,host_port,use_debug):
    app = Flask(__name__)
    app.register_blueprint(rest_api)
    app.run(host=host_address, port=host_port, debug=use_debug)

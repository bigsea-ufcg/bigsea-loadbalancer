import os


def cmd(arguments):
    if arguments.configuration is not None:
        if not os.path.isfile(arguments.configuration):
            message = ("Can't find configuration file %s" %
                       arguments.configuration)
            raise Exception(message)
    else:
        if not os.path.isfile('load_balancer.cfg'):
            message = "Can't find configuration file load_balancer.cfg"
            raise Exception(message)

    return arguments


def configuration_file(conf):
    for section in conf.sections():
        for option in conf.options(section):
            if conf.get(section, option):
                pass
            else:
                message = ("Empty value for option %s in section %s") % (
                    option, section
                )
                raise Exception(message)

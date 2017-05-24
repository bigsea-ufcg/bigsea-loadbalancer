import logging


class Log:

    def __init__(self, name, output_file_path):
        formatter = logging.Formatter(
            fmt='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)
        handler = logging.FileHandler(output_file_path)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, text):
        self.logger.info(text)


def configure_logging():
    logging.basicConfig(level=logging.INFO)

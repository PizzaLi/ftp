# -*- coding: utf-8 -*-
import logging

class Logger(object):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s[%(name)s][%(levelname)s]: %(message)s'
                            )

    def get_logger(self, name):
        return logging.getLogger(name)

logger = Logger()

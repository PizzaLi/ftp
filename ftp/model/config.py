# -*- coding: utf-8 -*-
import yaml
from ftp.lib.logger import logger

logger = logger.get_logger('ftp.model.config')


class FtpServerConfig(object):
    def __init__(self, file_path):
        self.file_obj = open(file_path)
        self.config_cache = None

    @property
    def config(self):
        if self.config_cache is None:
            try:
                self.config_cache = yaml.load(self.file_obj)
            except yaml.YAMLError:
                logger.error('Error in configuration file')
            finally:
                self.close_file()
        return self.config_cache

    @property
    def server_address(self):
        server_config = self.config.get('ftpserver')
        host = server_config.get('host')
        port = int(server_config.get('port'))
        return host, port

    @property
    def user_file(self):
        return self.config.get('ftpserver').get('user_file')

    def close_file(self):
        self.file_obj.close()

ftpserverconfig = FtpServerConfig('/Users/pizza/python/projects/app_junior/ftp/appftp.yaml')

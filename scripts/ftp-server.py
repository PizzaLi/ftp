# -*- coding: utf-8 -*-
from ftp.core.server import FtpServer

if __name__ == '__main__':
    ftpserver = FtpServer()
    ftpserver.serve_forever()

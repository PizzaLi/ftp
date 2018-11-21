# -*- coding: utf-8 -*-

"""
Usage:
  ftp-cli.py <host> <port>
  ftp-cli.py -h | --help

Options:
  -h --help     Show this screen.
"""

from docopt import docopt
from ftp.core.client import FtpClient


def main():
    # Get the arguments
    args = docopt(__doc__)
    host = args.get('<host>')
    port = int(args.get('<port>'))
    server_address = host, port
    # Create a ftpclient instance.
    ftpclient = FtpClient(server_address)


if __name__ == '__main__':
    main()

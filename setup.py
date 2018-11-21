# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='ftp',
    version='1.0',
    author='Pizza Li',
    author_email='libishengno1@foxmail.com',
    description='Simple ftp server and client',
    scripts=['scripts/ftp-server', 'scripts/ftp-client'],
    install_requires=['docopt>=0.6.2', 'PyYAML==3.12'],
)

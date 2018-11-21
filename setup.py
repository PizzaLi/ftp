# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils import setup

setup(
    name='ftp',
    version='1.0',
    packages=find_packages(),
    author='Pizza Li',
    author_email='libishengno1@foxmail.com',
    description='Simple ftp server and client',
    scripts=['scripts/ftp-server.py', 'scripts/ftp-cli.py'],
    install_requires = ['docopt>=0.6.2'],
)

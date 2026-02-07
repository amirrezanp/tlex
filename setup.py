# setup.py
from setuptools import setup, find_packages

setup(
    name='tlex',
    version='1.3.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'tlex = tlex.main:main',
        ],
    },
    install_requires=[
        'rich',
        'jsonpickle',
        'paramiko',
        'cryptography',
        'pyqrcode',
    ],
    description='Advanced Secure Port Forwarding Tunnel with TUI and Docker',
    author='Amirreza NP',
    url='https://github.com/amirrezanp/tlex',
)
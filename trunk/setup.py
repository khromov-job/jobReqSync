# -*- coding: utf-8 -*-

from os.path import join, dirname
from setuptools import setup, find_packages

misc = {}
with open('request_sync/misc.py') as f:
    exec(f.read(), misc)
app_name = misc['__appname__']

setup(
    name=app_name,
    version='1.0.3',
    description='Приложение синхронизации заявок между внутренним и внешним сегментом ЦБГД',
    long_description=open(join(dirname(__file__), 'README.rst')).read(),
    author='N.Nikonov, A.Khromov',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages(),
    setup_requires=['nose'],
    test_suite='nose.collector',
    install_requires=[
        'PyYAML ~= 3.0',
        'requests ~= 2.0',
        'deepdiff ~= 2.0',
        'jobLauncher ~= 1.0',
    ],
    data_files=[('/etc/opt/' + app_name, ['etc/log_settings.yaml', 'etc/settings.yaml'])],
    entry_points={
        'console_scripts': ['reqsync=request_sync:main'],
    },
)

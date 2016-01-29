#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='clarify_brightcove_sync',
    version='0.0.1',
    description='Commandline tool to sync a Brightcove video library to Clarify.',
    long_description=readme + '\n\n' + history,
    author='Ivo Rothschild',
    author_email='ivo@clarify.io',
    url='https://github.com/Clarify/clarify_brightcove_sync',
    packages=[
        'clarify_brightcove_sync',
    ],
    scripts=['bin/clarify_brightcove_sync'],
    package_dir={'clarify_brightcove_sync':
                 'clarify_brightcove_sync'},
    include_package_data=True,
    install_requires=[
        'requests',
        'clarify_python'
    ],
    license="MIT",
    zip_safe=False,
    keywords='clarify_brightcove_sync clarify brightcove video audio search',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
    ],
    tests_require=[
        # httpretty 0.8.11 breaks due to being unable to find / open
        # a requirements file
        # httpretty 0.8.12 breaks due to having invalid python3 lambda
        # syntax
        'httpretty<=0.8.10'
    ],
    test_suite='tests',
)

#!/usr/bin/env python
import os
import sys
from setuptools import setup, find_packages
rootdir = os.path.abspath(os.path.dirname(__file__))
name = "jaypage"
long_description = open(os.path.join(rootdir, 'README.md')).read().strip()
VERSION = open(os.path.join(rootdir, 'VERSION')).read().strip()
setup(name='jay' + name,
      version=VERSION,
      description='jaypage',
      long_description=long_description,
      url='',
      author='gardsted',
      author_email='gardsted@gmail.com',
      license='MPL',
      classifiers=[
          'Development Status :: 1 - Planning',
          'Environment :: Console',
          'License :: OSI Approved :: Mozilla Public License',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
      ],
      keywords='mail',
      packages=["jaypage"]
)

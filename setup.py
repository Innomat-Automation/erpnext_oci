# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in erpnext_oci/__init__.py
from erpnext_oci import __version__ as version

setup(
	name='erpnext_oci',
	version=version,
	description='Open Catalog Interface for ERPNext',
	author='Asprotec AG',
	author_email='m.mueller@asprotec.ch',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)

#!/usr/bin/env python
from setuptools import setup, find_packages 
 
version = '0.1'
 
setup(
    name = "TCWiki",
    version = version,
    description = "Django wiki engine with Creole Syntax",
    long_description = "Django wiki engine using Creole syntax, designed to integrate with with other applications",
    keywords = 'web wiki django creole',
    license = 'ISC',
    author = 'Element43 & EForge Project',
    author_email = 'support@e43.eu',
    url = '',
    zip_safe = False,
    packages = find_packages(),
    include_package_data = True,
    install_requires = [
        "django>=1.2.1",
        "creoleparser>=0.7.2"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: ISC License",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)

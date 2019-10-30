#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import Command, setup, find_packages
from setuptools.command.test import test as TestCommand

import versioneer

# Package meta-data.
NAME = 'siliqua'
DESCRIPTION = 'Modular light wallet for the NANO cryptocurrency'
URL = 'https://github.com/Matoking/siliqua'
EMAIL = 'jannepulk@gmail.com'
AUTHOR = 'Janne Pulkkinen'
REQUIRES_PYTHON = '>=3.6.0'

# What packages are required for this module to be executed?
REQUIRED = [
    'nanolib>=0.4', 'msgpack>=0.6', 'cryptography>=2.6', 'appdirs>=1.4',
    'click>=7.0', 'toml>=0.10', 'aiohttp>=3.5', 'filelock>=3.0', 'ijson>=2.5',
    'python-rapidjson>=0.8'
]


# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.rst' is present in your MANIFEST.in file!
with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass into py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import shlex
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'.format(sys.executable))

        self.status('Uploading the package to PyPi via Twine…')
        os.system('twine upload dist/*')

        self.status('Pushing git tags…')
        os.system('git tag v{0}'.format(versioneer.get_version()))
        os.system('git push --tags')

        sys.exit()


cmdclass = versioneer.get_cmdclass()
cmdclass.update({
    'upload': UploadCommand,
    'pytest': PyTest,
})

# Where the magic happens:
setup(
    name=NAME,
    version=versioneer.get_version(),
    description=DESCRIPTION,
    long_description=long_description,
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages("src"),
    package_dir={
        "": "src"
    },
    package_data={"": ["LICENSE"]},
    install_requires=REQUIRED,
    setup_requires=[
        "sphinx", "sphinx-tabs", "sphinxcontrib-apidoc"
    ],
    extras_require={
        "sphinx": ["sphinx-tabs", "sphinxcontrib-apidoc"]
    },
    tests_require=["pytest"],
    include_package_data=True,
    license='CC0',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        #  'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Topic :: Office/Business :: Financial',
    ],
    entry_points={
        "console_scripts": [
            "siliqua = siliqua.cli:main"
        ],
        "siliqua.plugins.ui": [
            "stdio = siliqua.ui.stdio:StdioUI",
        ]
    },
    # $ setup.py publish support.
    cmdclass=cmdclass,
    command_options={
        'build_sphinx': {
            'project': ('setup.py', NAME),
            'version': ('setup.py', versioneer.get_version()),
            'source_dir': ('setup.py', 'docs')
        },
    }
)

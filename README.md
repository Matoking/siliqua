Siliqua
=======

[![image](https://img.shields.io/pypi/v/siliqua.svg)](https://pypi.org/project/siliqua/)
[![Coverage Status](https://coveralls.io/repos/github/Matoking/siliqua/badge.svg?branch=master)](https://coveralls.io/github/Matoking/siliqua?branch=master)
[![Build Status](https://travis-ci.com/Matoking/siliqua.png?branch=master)](https://travis-ci.com/Matoking/siliqua)
[![image](https://readthedocs.org/projects/siliqua/badge/?version=latest)](https://siliqua.readthedocs.io/en/latest/?badge=latest)

Modular light wallet for the NANO cryptocurrency with a command-line interface.

**This application is under early development and any features are subject to change at the moment. Use at your own risk.**

Features
========
* Optional two-level encryption
  * Wallet secrets (private keys and seed) and the wallet itself can be encrypted separately
* Watching-only accounts
* Supports NANO seeds
* Transaction timestamps and descriptions
* Portable wallet files for easy backups with timestamps and details intact
* NANO node and NanoVault server support
* JSON output for easy integration with scripts

Installation
============

You can install the reference command-line interface using pip:

```
pip install siliqua
```

Siliqua requires a working build environment for the C extensions. For example, on Debian-based distros you can install the required Python header files and a C compiler using the following command:

```
apt install build-essential python3-dev
```

virtualenv is recommended instead of a system-wide installation. For example, to create a virtualenv and install Siliqua inside it:

```
python3 -mvenv venv
source venv/bin/activate
pip install siliqua
```

To deactivate the virtualenv, run:

```
deactivate
```

After installation, you can read the [Getting Started](https://siliqua.readthedocs.io/en/latest/user/getting_started.html) section of the documentation.

Documentation
=============

For user and developer documentation, see online documentation at [Read the Docs](https://siliqua.readthedocs.io/en/latest/).

You can also build the documentation yourself by running `python setup.py build_sphinx`.

Donations
=========

**xrb_35xiwe88pqxemiwffi5hrgwyujxg1su948zh8zhczdwwc75bqjb13fhddhke**

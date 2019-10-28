.. nanolib documentation master file, created by
   sphinx-quickstart on Sun Jan  6 14:58:17 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Siliqua's documentation!
===================================

Siliqua is a modular NANO light wallet written in Python. It comes with numerous
different features:

- Optional two-level encryption
   - Wallet secrets (private keys and seed) and the wallet itself can be encrypted separately to improve security.
- Watching-only accounts
- Supports NANO seeds
- Transaction timestamps and descriptions
- Portable wallet files allowing wallets to be backed up with timestamps and comments intact
- NANO node and NanoVault server support
- JSON output for easy integration with scripts

##########
User guide
##########

.. toctree::
   :maxdepth: 3

   user/getting_started
   user/commands

###########
Development
###########

.. toctree::
   :maxdepth: 3

   developer/architecture
   developer/api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

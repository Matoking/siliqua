Getting started
===============

Siliqua comes with a reference user interface (`stdio`) for command line
usage.

Creating a wallet
-----------------

After you have installed, you should be able to use `siliqua` command line
command to run different commands. Start by creating your wallet:

.. code-block:: console

   $ siliqua create-wallet <WALLET PATH>


After you have created your wallet, you can get a list of accounts by running
`list-accounts`.

.. code-block:: console

   $ siliqua --wallet <WALLET PATH> list-accounts


You can synchronize the wallet with the network by running `sync`. This will
synchronize all the accounts' blockchains as well as pocket any pending
NANO.

.. note::

   You will need to configure your node before you can synchronize with
   the network.

.. code-block:: console

   $ siliqua --wallet <WALLET PATH> sync

Finally, you can send NANO by using the `send` command.

.. code-block:: console

   $ siliqua --wallet <WALLET PATH> <SOURCE> <DESTINATION> <AMOUNT>

All the commands available in the CLI interface are documented in :ref:`user/commands`.


Configuration
-------------

Siliqua creates configuration files when running the command for the first
time. The location of configuration files can be checked by running:

.. code-block:: console

   $ siliqua --help

A custom location for configuration files can also be chosen using the
`--config` command line parameter.

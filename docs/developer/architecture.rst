Architecture
============

Siliqua consists roughly of five different components:

- :class:`siliqua.wallet.Wallet`

  Wallet with optional encryption that can be saved into JSON format
- :class:`siliqua.network.BaseNetworkPlugin`

  Network provider that updates the wallet with new blocks and
  broadcasts unconfirmed blocks into the NANO network
- :class:`siliqua.work.BaseWorkPlugin`

  Work provider that polls the wallet for missing proof-of-work and generates
  them
- :class:`siliqua.server.WalletServer`

  The main "server" instance that's responsible for handling wallet, network
  and work providers and communication between them to keep the wallet
  up-to-date
- :class:`siliqua.ui.BaseUI`

  The user interface that creates the server instance and allows the user to
  manage their wallet

Of these components, network, work and UI are modular and can be selected
on startup using either a configuration file or command-line options.
New components can be implemented by subclassing the corresponding classes
and exposing them using `setuptools' entrypoint feature <https://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins>`_.
For example, a new work component could be created that performs PoW generation
using a 3rd party service.

Network
-------

Each network server has the following queues:

- :attr:`siliqua.network.BaseNetworkPlugin.processed_block_queue`

  Blocks received from the network that correspond to accounts in the wallet.
  The network server pushes blocks into this queue.
- :attr:`siliqua.network.BaseNetworkPlugin.pocketable_block_queue`

  Send blocks that can be pocketed by accounts in the wallet.
  The network server pushes blocks into this queue.
- :attr:`siliqua.network.BaseNetworkPlugin.broadcast_block_queue`

  Blocks created by the wallet that are pending broadcast into the network.
  The wallet pushes blocks into this queue indirectly by :meth:`siliqua.server.WalletServer.update`.

All the queues operate as FIFO queues: oldest blocks are pushed into queues
first and oldest blocks are pulled from the queues first.

:attr:`siliqua.network.BaseNetworkPlugin.account_sync_statuses` is a dictionary
following an account ID to :class:`siliqua.network.AccountSyncStatus` mapping.
The dictionary is used to keep track of which accounts are in the wallet
and which accounts have finished synchronizing with the network.

Proof-of-work
-------------

Each work server consists of :attr:`siliqua.work.BaseWorkPlugin.work_units` dictionary
following a "work block hash" to :class:`siliqua.work.WorkUnit` mapping.

This dictionary can be accessed simultaneously by the wallet and the work server
itself. To prevent race conditions, the lock :attr:`siliqua.work.BaseWorkPlugin.work_lock`
is used whenever the dictionary is accessed.

User interface
--------------

Each user interface plugin must override the following methods:

- :meth:`siliqua.ui.BaseUI.get_cli`

  Returns either a :class:`click.Group` instance if the user interface
  consists of multiple commands or a :class:`click.Command` if the
  user interface only consists of a single command.
  Multiple command approach is used by the reference ``stdio`` command-line
  implementation, while single command approach would be ideal for
  graphical user interfaces.

- :meth:`siliqua.ui.BaseUI.run`

  Takes a :class:`siliqua.server.WalletServer` instance and a :class:`click.Context`
  instance and is responsible for starting the user interface.
  The :class:`siliqua.server.WalletServer` might be missing some components,
  so the method is responsible for either prompting the user to configure
  the application or report an error due to insufficient configuration.

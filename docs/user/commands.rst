.. _user/commands:

Commands
========

Response format
---------------

Each command returns a JSON-formatted response that follows the
JSend_ specification. This allows the command-line interface to be used
as part of differnt applications.


Command reference
-----------------

add-account
^^^^^^^^^^^

Add an account into the wallet.

If private key is provided, the account will be spendable.
If public key or account ID is provided, the account is watching-only.
Only one of these parameters can be provided.

Parameters
""""""""""

- ``account_id`` (option) = account ID to add as a watching-only account
- ``public_key`` (option) = public key to add as a watching-only account
- ``private_key`` (option/env) = private key to add as a spendable account. Can be provided securely with env var ``PRIVATE_KEY``.

Results
"""""""

.. tabs::

   .. group-tab:: Add account

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> add-account --account-id xrb_3bei1ezzawywwzuq4a6jqabhefb5ykigzq8c9ixooi1qp1o375syh8auyzqr

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_3bei1ezzawywwzuq4a6jqabhefb5ykigzq8c9ixooi1qp1o375syh8auyzqr"
             },
             "status": "success"
         }

   .. group-tab:: Account exists

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> add-account --account-id xrb_3bei1ezzawywwzuq4a6jqabhefb5ykigzq8c9ixooi1qp1o375syh8auyzqr

      .. code-block:: json

         {
             "data": {
                 "error": "account_already_exists"
             },
             "message": "Account already exists in the wallet",
             "status": "error"
         }


add-to-address-book
^^^^^^^^^^^^^^^^^^^

Add an account ID into the wallet's address book.

If account already exists in the address book, the name will be overwritten.

Parameters
""""""""""

- ``account_id`` (positional) = account ID to add to the address book
- ``name`` (positional) = name of the account ID

Results
"""""""

.. tabs::

   .. group-tab:: Add account ID

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> add-to-address-book xrb_3bei1ezzawywwzuq4a6jqabhefb5ykigzq8c9ixooi1qp1o375syh8auyzqr "Alice's account"

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_3bei1ezzawywwzuq4a6jqabhefb5ykigzq8c9ixooi1qp1o375syh8auyzqr",
                 "name": "Alice's account"
             },
             "status": "success"
         }

calculate-key-iteration-count
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Calculate the key iteration count given the amount of seconds.

Key iteration count is used is used when encrypting the wallet to determine
the amount of rounds required to derive the passphrase. Higher key iteration
counts improve security by requiring more processing time to test a passphrase.

Generated key iteration counts can be used in conjuction with the
`change-encryption`_ command.

Parameters
""""""""""

- ``seconds`` (positional) = amount of seconds used for deriving the key

Results
"""""""

.. tabs::

   .. group-tab:: Calculate iteration count

      .. code-block:: console

         $ siliqua calculate-key-iteration-count --seconds 5

      .. code-block:: json

         {
             "data": {
                 "key_iteration_count": 17795321,
                 "seconds": 5.0
             },
             "status": "success"
         }


change-account-representative
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Change the representative for the given account.

If the account has received NANO, a new block will also be created.

Parameters
""""""""""

- ``account_id`` (positional) = spendable account ID in the wallet
- ``representative`` (positional) = representative account ID
- ``wait_until_confirmed/no_wait_until_confirmed`` (flag) = whether to wait until the created block is confirmed. Default is true.
- ``timeout`` (option) = how long to wait in seconds until the block is confirmed. If not provided, command will wait until the block is confirmed. Default is 0, meaning the wallet will wait indefinitely until the block is confirmed.

Results
"""""""

.. tabs::

   .. group-tab:: Change (empty account)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> change-account-representative xrb_36ge4u85bye196k6mgte9qh37sk9g8r1ih1y1wxy9hidkmooapcpqpobe6mr xrb_1xx8ihj8gxg874gat4repqzgdtffridnbaxewymxh45zf6rd3oumosfbqbc8

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_36ge4u85bye196k6mgte9qh37sk9g8r1ih1y1wxy9hidkmooapcpqpobe6mr",
                 "representative": "xrb_1xx8ihj8gxg874gat4repqzgdtffridnbaxewymxh45zf6rd3oumosfbqbc8"
             },
             "status": "success"
         }

   .. group-tab:: Change (new block)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> change-account-representative xrb_36ge4u85bye196k6mgte9qh37sk9g8r1ih1y1wxy9hidkmooapcpqpobe6mr xrb_1xx8ihj8gxg874gat4repqzgdtffridnbaxewymxh45zf6rd3oumosfbqbc8

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_36ge4u85bye196k6mgte9qh37sk9g8r1ih1y1wxy9hidkmooapcpqpobe6mr",
                 "representative": "xrb_1xx8ihj8gxg874gat4repqzgdtffridnbaxewymxh45zf6rd3oumosfbqbc8",
                 "hash": "128C115463857249197E582D46DE640B7D568EDA952FD42465641E7FD4732442",
                 "confirmed": true,
                 "rejected": false
             },
             "status": "success"
         }

   .. group-tab:: Change (new block, failed)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> change-account-representative xrb_36ge4u85bye196k6mgte9qh37sk9g8r1ih1y1wxy9hidkmooapcpqpobe6mr xrb_1xx8ihj8gxg874gat4repqzgdtffridnbaxewymxh45zf6rd3oumosfbqbc8

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_36ge4u85bye196k6mgte9qh37sk9g8r1ih1y1wxy9hidkmooapcpqpobe6mr",
                 "representative": "xrb_1xx8ihj8gxg874gat4repqzgdtffridnbaxewymxh45zf6rd3oumosfbqbc8",
                 "hash": "128C115463857249197E582D46DE640B7D568EDA952FD42465641E7FD4732442",
                 "confirmed": false,
                 "rejected": true,
                 "block_error": "fork"
             },
             "status": "success"
         }

change-encryption
^^^^^^^^^^^^^^^^^

Change the wallet's encryption settings.

You can encrypt secrets, the wallet file or both. Encrypting secrets means
a passphrase is required when spending or receiving NANO. Encrypting the wallet
means that a passphrase is required to open the wallet.

Encryption can also be removed using this command.

Parameters
""""""""""

- ``new_passphrase`` (option/env) = passphrase to use if encrypting the wallet. Can be provided securely with env var ``NEW_PASSPHRASE``.
- ``encrypt_secrets/no_encrypt_secrets`` (flag) = encrypt the secrets
- ``encrypt_wallet/no_encrypt_wallet`` (flag) = encrypt the wallet
- ``key_iteration_count`` (option) = key iteration count to use when encrypting the wallet. See `calculate-key-iteration-count`_ command for details. If not provided, key iteration count will be calculated with the target of 1 second.


Results
"""""""

.. tabs::

   .. group-tab:: Encrypt secrets

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> change-encryption --encrypt-secrets --no-encrypt-wallet

      .. code-block:: json

         {
            "data": {
                "key_iteration_count": 3561754,
                "message": "Encryption changed on wallet /home/user/name.wallet",
                "secrets_encrypted": true,
                "wallet_encrypted": false
            },
            "status": "success"
         }

change-gap-limit
^^^^^^^^^^^^^^^^

Change the wallet's gap limit.

New accounts will be generated if necessary to fill the gap.

Parameters
""""""""""

- ``gap_limit`` (positional) = new gap limit

Results
"""""""

.. tabs::

   .. group-tab:: Increase gap limit from 20 to 25

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> change-gap-limit 25

      .. code-block:: json

         {
             "data": {
                 "gap_limit": 25,
                 "new_accounts": [
                     "xrb_1trrz5xwgqnixfm8yscbbyjejm8rbuyy7bjrmhozbbpr7jrku9aptqing4t1",
                     "xrb_3yjy4bjaibext7mmuybwxao46suchgs4gufccboxhhc5ne4jzufees3wwch6",
                     "xrb_3a8i79r7kbwzkufitjhh7bgox6udd5gqrghipw4qox1u7s8r3fxz3hq6ndxz",
                     "xrb_1g9r615arrc3krd98eoh5rrrmo7xdcz31myqy9n5bqbgr7nq763qrxa7g7zk",
                     "xrb_38pchni9t53zaopix3p8uxofamb5on3bn9fnbdxtfbsdo8gu35ruphch4whc"
                 ]
             },
             "status": "success"
         }

clear-block-description
^^^^^^^^^^^^^^^^^^^^^^^

Clear the block's description.

The block must belong to one of the accounts in the wallet.

Parameters
""""""""""

- ``block_hash`` (positional) = block hash

Results
"""""""

.. tabs::

   .. group-tab:: Clear block description

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> clear-block-description E13CBA3CADA1A9CB2AE3B2848338B8CFBFF272957BA0007565064992CB3CCDBF

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_1mex5xsc5xt4yxrbytxff6sdoj9qsjz17ywxs31yoqem8aes8yocqb8n3r1j",
                 "hash": "E13CBA3CADA1A9CB2AE3B2848338B8CFBFF272957BA0007565064992CB3CCDBF"
             },
             "status": "success"
         }

   .. group-tab:: Block not found

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> clear-block-description 73664497AFD120343527CB86BFABADEB2D30A4EEE35D576EA928266F72E72AD0

      .. code-block:: json

         {
             "data": {
                 "error": "block_not_found"
             },
             "message": "Block not found in the wallet",
             "status": "error"
         }

clear-account-name
^^^^^^^^^^^^^^^^^^

Clear the account's name.

Parameters
""""""""""

- ``account_id`` (positional) = account ID

Results
"""""""

.. tabs::

   .. group-tab:: Clear account name

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> clear-account-name xrb_144rsgyugo8137rwgndgkgt6u174xuwpkebgpngpq5oi5oi65fjf6qpog8t4

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_144rsgyugo8137rwgndgkgt6u174xuwpkebgpngpq5oi5oi65fjf6qpog8t4"
             },
             "status": "success"
         }

create-wallet
^^^^^^^^^^^^^

Create a new wallet.

Encryption settings can be created at the same time using the same parameters
as the `change-encryption`_ command.

Parameters
""""""""""

- ``wallet_path`` (positional) = where to save the created wallet
- ``seed`` (option/env) = seed to use for generating accounts automatically.
  If not provided, one will be generated automatically.
  Can be provided securely with ``SEED`` env var.
- ``encrypt_secrets/no_encrypt_secrets`` (flag) = encrypt the secrets
- ``encrypt_wallet/no_encrypt_wallet`` (flag) = encrypt the wallet
- ``passphrase`` (option/env) = passphrase to use if encrypting the wallet. Can be provided securely with env var ``PASSPHRASE``.
- ``gap_limit`` (option) = how many unused accounts are generated using the seed at most.
   Set to ``0`` to disable automatic account generation entirely.
   Defaults to ``20``.
   More accounts can be generated manually using the `generate-account`_ command.
- ``key_iteration_count`` (option) = key iteration count to use when encrypting the wallet.
  See `calculate-key-iteration-count`_ command for details.
  If not provided, key iteration count will be calculated with the target of 1 second.

Results
"""""""

.. tabs::

   .. group-tab:: Create wallet

      .. code-block:: console

          $ siliqua create-wallet --gap-limit 50 <WALLET PATH>

      .. code-block:: json

         {
             "data": {
                 "message": "Saved wallet to <WALLET PATH>",
                 "secrets_encrypted": false,
                 "wallet_encrypted": false
             },
             "status": "success"
         }

generate-account
^^^^^^^^^^^^^^^^

Generate new account(s) from wallet seed.

Wallet's gap limit is ignored when generating accounts manually using this command.

Parameters
""""""""""

- ``count`` (option) = how many accounts to generate. Defaults to 1.

Results
"""""""

.. tabs::

   .. group-tab:: Generate 5 accounts

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> generate-account --count 5
      .. code-block:: json

         {
             "data": {
                 "new_accounts": [
                     "xrb_3cbyjh1bdayo74cuaaggiez7fwmtjyue6z7ozeamodnxdwwaiqmwde8pcjux",
                     "xrb_3e3f1fz49wpspk49iutugz89ndcxf6i7wsyexhffezrfex6i9ifcn79j4459",
                     "xrb_1hcgz4jtcwacqn8gh5pibg99ea31mk4hxwuozkc9n9f5zr7jkm1a1etu5u8z",
                     "xrb_3bfyri6akc5qhikjuaou4gm61gkkfmc4i8jybt9i65gdcfeh133hzkrxeboh",
                     "xrb_3dw6hboef9skneo1ck3z3tgaff6k798bnnbwxh444a4akxpx835e7z9dhzxo"
                 ]
             },
             "status": "success"
         }

get-account-private-key
^^^^^^^^^^^^^^^^^^^^^^^

Get the private key for a spendable account.

Parameters
""""""""""

- ``account_id`` (positional) = account ID of the spendable account

Results
"""""""

.. tabs::

   .. group-tab:: Get private key

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> get-account-private-key xrb_1qrb86ngd4aqe7n9s4xqrhu5tmxb7mph6kp46qz9xhmg8keomgsemmsrwsep

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_1qrb86ngd4aqe7n9s4xqrhu5tmxb7mph6kp46qz9xhmg8keomgsemmsrwsep",
                 "private_key": "7bc232f918fc3dc8e2e29d45dc6e1d6962c9e4c24a9da315a1bccd04a28c6f66"
             },
             "status": "success"
         }

   .. group-tab:: Account not spendable

         $ siliqua --wallet <WALLET PATH> get-account-private-key xrb_3qwunbihqbp1p731ah63qug58m5g8x376ifhqz9oyqqctdaj6p39sy36yyu8

   .. code-block:: json

      {
          "data": {
              "error": "spendable_account_required"
          },
          "message": "Account with a private key is required for this operation",
          "status": "error"
      }

get-balance
^^^^^^^^^^^

Get the balance for a wallet.

The balances are reported in raw.

Parameters
""""""""""

This command takes no parameters.

Results
"""""""

.. tabs::

   .. group-tab:: Get balance

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> get-balance

      .. code-block:: json

         {
             "data": {
                 "accounts": {
                     "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek": {
                         "balance": "200000000",
                         "spendable": true
                     },
                     "xrb_11bj6gy13rowhm1zchqgjhxjszp9axaw5qfkybjg7acbaregs49ksj4h5jck": {
                         "balance": "0",
                         "spendable": true,
                         "name": "Savings"
                     },
                     "xrb_13f6d1aa44hc63uw8yxofhr37xp3aje4hd8nrpfbidauc1w7fjngogqp9apa": {
                         "balance": "0",
                         "spendable": true
                     },
                 },
                 "spendable_balance": "200000000",
                 "unspendable_balance": "200000000"
             },
             "status": "success"
         }

get-block
^^^^^^^^^

Get a block from the wallet by its block hash.

The block must belong to an account's blockchain. The block can also be
retrieved if it was pocketed by one of the accounts in the wallet.

Parameters
""""""""""

- ``block_hash`` (positional) = block hash of the block to retrieve

Results
"""""""

.. tabs::

   .. group-tab:: Get block (account)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> get-block 6110BF09D268F258DC10DEA89CE0FE05D6003E8D270E0DBD94C759CD7E225A4F

      .. code-block:: json

         {
             "data": {
                 "amount": "1100000000000000000000000000000",
                 "balance": "1101577602024399729402216185856",
                 "block_data": {
                     "account": "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek",
                     "balance": "1101577602024399729402216185856",
                     "link": "CFE6C4C354480252095F11218251F1DF078A9F19E96D77E8239CB38CFF2B89BD",
                     "link_as_account": "xrb_3mz8rm3oak14ca6oy6b3ibaz5qr9jchjmtdfgzn4997mjmzkq4fxahx6p4sa",
                     "previous": "6C659CECE6B30323B3A3D4CD2B8C6BA1A16D8CF931379A58F5D97055D06FE1A7",
                     "representative": "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek",
                     "signature": "80D654FE1288B4044003E1B4E9CD06ED8CB332459561D17A159C3ECE3CB8E6DB28DAE978B0118FD46987F1A90DF1B2B36355BA1395FDC0815D36A9E8D82BB302",
                     "type": "state",
                     "work": "f38f33869f120faa"
                 },
                 "confirmed": true,
                 "has_signature": true,
                 "has_work": true,
                 "hash": "6110BF09D268F258DC10DEA89CE0FE05D6003E8D270E0DBD94C759CD7E225A4F",
                 "is_link_block": false,
                 "timestamp": {
                     "date": "1556254077",
                     "source": "node"
                 },
                 "tx_type": "receive"
             },
             "status": "success"
         }

   .. group-tab:: Get block (pocketed)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> get-block CFE6C4C354480252095F11218251F1DF078A9F19E96D77E8239CB38CFF2B89BD

      .. code-block:: json

         {
             "data": {
                 "amount": "-1100000000000000000000000000000",
                 "block_data": {
                     "account": "nano_3ca14w7joxe9yzaih9sc3r74scmek3tdyj8so34hhfsg7unbyp9oh1eem8so",
                     "balance": "0",
                     "link": "ECAB1C2AFF0059E79FD7B9B33C2E2EA0FE825EA753D121CBBE3E0AB004B7F45C",
                     "link_as_account": "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek",
                     "previous": "7D75D99ACCDF5558B66D92ED50ADD160DBFD469602AB30ABA77AAEBE17FC597E",
                     "representative": "nano_374qyw8xwyie1hhws4cfo1fbrkis44dd6aputrujmrteeexcyag4ej84kkni",
                     "signature": "4BC1C2AF48ECF4A085BF476B961BAD9954C3558337E3F1F60EAEBDA592ABDF5FFA2B7C12D8336C466CD5FAA6ACFF14C43FAD71CF81B72D26D3C7610AA3598C08",
                     "type": "state",
                     "work": "80501b2305ce7ea1"
                 },
                 "confirmed": true,
                 "has_signature": true,
                 "has_work": true,
                 "hash": "CFE6C4C354480252095F11218251F1DF078A9F19E96D77E8239CB38CFF2B89BD",
                 "is_link_block": true,
                 "timestamp": {
                     "date": "1556254077",
                     "source": "node"
                 },
                 "tx_type": "send"
             },
             "status": "success"
         }

get-wallet-seed
^^^^^^^^^^^^^^^

Get the wallet seed used to generate accounts.

The wallet seed can be copied in order to be used in other compatible
NANO wallets.

Parameters
""""""""""

This command takes no parameters.

Results
"""""""

.. tabs::

   .. group-tab:: Get wallet seed

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> get-wallet-seed

      .. code-block:: json

         {
             "data": {
                 "seed": "ceab841e30ee5d9a422d9761e96f459a2fc9e3730a827ef6e4ec92385ad5f6c6"
             },
             "status": "success"
         }

list-accounts
^^^^^^^^^^^^^

List all accounts in the wallet.

This command accepts pagination parameters, which are described in section
`Pagination parameters`_.

Parameters
""""""""""

- ``limit`` (option) = how many accounts to return at most. Defaults to 20.
- ``offset`` (option) = how many results to skip. Defaults to 0, meaning results start from the first account.
- ``descending/no_descending`` (flag) = whether to return results in a descending order (newest to oldest). Defaults to `no_descending`, meaning oldest accounts are returned first.

Results
"""""""

.. tabs::

   .. group-tab:: Get 5 first accounts

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> list-accounts --limit 5

      .. code-block:: json

         {
             "data": {
                 "accounts": [
                     {
                         "account_id": "xrb_1ifp35tpx8fbei9q4mbbgrzjwffaozygkbtngu7rt9hcd5icimgbmsa6a1gi",
                         "balance": "0",
                         "head": null
                     },
                     {
                         "account_id": "xrb_3ro4mstgdx94ujk6dzom9z6nb7phkwhtg8ny5yab7hybjdaooua1hhsrxcnj",
                         "balance": "0",
                         "head": null
                     },
                     {
                         "account_id": "xrb_1zpphfhw98nktirzthr1i4ek17ouqm4g1jpzw7etx9p5amrfx87s1jfadse7",
                         "balance": "0",
                         "head": null
                     },
                     {
                         "account_id": "xrb_1r9rhkukii9acz9ttgysz4sohaxcw97upd3pt8pnbpxodpoa8ckju4ycitye",
                         "balance": "0",
                         "head": null,
                         "name": "Savings"
                     },
                     {
                         "account_id": "xrb_349ufmz1oxmi17xt91d74ux9duefkp8escijct5nezbbhs1jnsjg6wgyz7qm",
                         "balance": "0",
                         "head": null
                     }
                 ],
                 "count": 56
             },
             "status": "success"
         }

list-address-book
^^^^^^^^^^^^^^^^^

List all account IDs in the address book.

This command accepts pagination parameters, which are described in section
`Pagination parameters`_.

Parameters
""""""""""

- ``limit`` (option) = how many account IDs to return at most. Defaults to 20.
- ``offset`` (option) = how many account IDs to skip. Defaults to 0, meaning results start from the first account.
- ``descending/no_descending`` (flag) = whether to return results in a descending order (newest to oldest). Defaults to `no_descending`, meaning oldest account IDs are returned first.

Results
"""""""

.. tabs::

   .. group-tab:: Get 5 first account IDs

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> list-address-book --limit 5

      .. code-block:: json

         {
             "data": {
                 "addresses": {
                     "xrb_14cuejfpr58epnpxenirusimsrbwxbecin7a3izq1injptecc31qsjwquoe6": "Binance Cold Wallet #2",
                     "xrb_1ipx847tk8o46pwxt5qjdbncjqcbwcc1rrmqnkztrfjy5k7z4imsrata9est": "Developer Fund",
                     "xrb_3ing74j39b544e9w4yrur9fzuwges71ddo83ahgskzhzaa3ytzr7ra3jfsgi": "Huobi",
                     "xrb_3jwrszth46rk1mu7rmb4rhm54us8yg1gw3ipodftqtikf5yqdyr7471nsg1k": "Binance",
                     "xrb_3uip1jmeo4irjuua9xiyosq6fkgogwd6bf5uqopb1m6mfq6g3n8cna6h3tuk": "BitGrail Trustee"
                 },
                 "count": 6
             },
             "status": "success"
         }

list-blocks
^^^^^^^^^^^

List blocks for an account in the wallet.

This command accepts pagination parameters, which are described in section
`Pagination parameters`_.

Parameters
""""""""""

- ``account_id`` (positional) = account ID
- ``limit`` (option) = how many blocks to return at most. Defaults to 20.
- ``offset`` (option) = how many blocks to skip. Defaults to 0, meaning results start from the first account.
- ``descending/no_descending`` (flag) = whether to return results in a descending order (newest to oldest). Defaults to `descending`, meaning newest blocks are returned first.

Results
"""""""

.. tabs::

   .. group-tab:: Get 5 newest blocks

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> list-blocks nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek --limit 5

      .. code-block:: json

         {
             "data": {
                 "account_id": "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek",
                 "blocks": [
                     {
                         "amount": "306651099997808186481815220",
                         "balance": "1073884253124397539256219053748",
                         "confirmed": true,
                         "has_signature": true,
                         "has_work": true,
                         "hash": "F5D341432BACA445167F60E546273EB000CDE5DB08E9EC50C5D87B766C0EFE99",
                         "is_link_block": false,
                         "timestamp": {
                             "date": "1556321034",
                             "source": "node"
                         },
                         "tx_type": "receive"
                     },
                     {
                         "amount": "1000000000000000000000000000",
                         "balance": "1073577602024399731069737238528",
                         "confirmed": true,
                         "has_signature": true,
                         "has_work": true,
                         "hash": "350ED7088C7821861440FF29BDE3894C77B29E09D74334FBA75CFC07F0318BDB",
                         "is_link_block": false,
                         "timestamp": {
                             "date": "1556254078",
                             "source": "node"
                         },
                         "tx_type": "receive"
                     },
                     {
                         "amount": "0",
                         "balance": "1072577602024399731069737238528",
                         "confirmed": true,
                         "has_signature": true,
                         "has_work": true,
                         "hash": "20F7C7C6D3D3551360105B13C5EFE87EC927080F60D129211714B5A3DA49B793",
                         "is_link_block": false,
                         "timestamp": {
                             "date": "1556254078",
                             "source": "node"
                         },
                         "tx_type": "change"
                     },
                     {
                         "amount": "0",
                         "balance": "1072577602024399731069737238528",
                         "confirmed": true,
                         "has_signature": true,
                         "has_work": true,
                         "hash": "0C8884B9F032F91DFC21E99946D4880A07C790DD7EE9E91B5403D53E31F64EED",
                         "is_link_block": false,
                         "timestamp": {
                             "date": "1556254078",
                             "source": "node"
                         },
                         "tx_type": "change"
                     },
                     {
                         "amount": "1000000000000000000000000000",
                         "balance": "1072577602024399731069737238528",
                         "confirmed": true,
                         "has_signature": true,
                         "has_work": true,
                         "hash": "428488CDF8E75378411DFA5033DE20C320BE6F9CA56E033F1E06F505A88DBA06",
                         "is_link_block": false,
                         "timestamp": {
                             "date": "1556254078",
                             "source": "node"
                         },
                         "tx_type": "receive"
                     }
                 ],
                 "count": 23
             },
             "status": "success"
         }

remove-account
^^^^^^^^^^^^^^

Remove an account from the wallet.

Accounts generated from a seed can also be removed, but depending on the gap limit
they may be regenerated after running a different command.

Parameters
""""""""""

- ``account_id`` (positional) = account ID of the account to remove

Results
"""""""

.. tabs::

   .. group-tab:: Remove account

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> remove-account nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek

      .. code-block:: json

         {
             "data": {
                 "account_id": "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek"
             },
             "status": "success"
         }

   .. group-tab:: Account does not exist

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> remove-account nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek

      .. code-block:: json

         {
             "data": {
                 "error": "account_not_found"
             },
             "message": "Account not found in the wallet",
             "status": "error"
         }

remove-from-address-book
^^^^^^^^^^^^^^^^^^^^^^^^

Remove an account ID from the address book.

Parameters
""""""""""

- ``account_id`` (positional) = account ID to remove

Results
"""""""

.. tabs::

   .. group-tab:: Remove account ID

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> remove-account xrb_14cuejfpr58epnpxenirusimsrbwxbecin7a3izq1injptecc31qsjwquoe6

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_14cuejfpr58epnpxenirusimsrbwxbecin7a3izq1injptecc31qsjwquoe6"
             },
             "status": "success"
         }

   .. group-tab:: Account ID does not exist

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> remove-account xrb_14cuejfpr58epnpxenirusimsrbwxbecin7a3izq1injptecc31qsjwquoe6

      .. code-block:: json

         {
             "data": {
                 "error": "account_not_found"
             },
             "message": "Account not found in the wallet",
             "status": "error"
         }

send
^^^^

Send NANO from one account to another account.

Rejected block won't be saved into the wallet.

Parameters
""""""""""

- ``source`` (positional) = source account from which NANO is sent
- ``destination`` (positional) = destination account to which NANO is sent
- ``amount`` (positional) = amount of NANO to send. If a single integer is provided, *raw* is assumed to be the denomination.
- ``wait_until_confirmed/no_wait_until_confirmed`` (flag) = whether to wait until the generated block is confirmed. Default is true.
- ``txid`` (option) = optional wallet-specific transaction ID used for the transaction. If the same transaction ID already exists in the wallet, no NANO will be sent. Can be used to ensure transactions are idempotent.
- ``description`` (option) = optional description added to the block.
- ``timeout`` (option) = time to wait in seconds until the block is confirmed in the network before giving up. Timeout ignores the time taken to generate PoW. Default is 0, meaning the wallet will wait indefinitely until the blocks are confirmed.

Results
"""""""

.. tabs::

   .. group-tab:: Send 10 Mnano

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> send xrb_1h3h85s4nbuwbcuqxjpprzmsj3reqgfk4i8dzs7otfntff6sqdo9a6deqh3i xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7 "10 mnano"

      .. code-block:: json

         {
             "data": {
                 "hash": "66521D8FFE2C5E63993EDA8E5E2AFF35F2EC9BA993C8751DAE532F439F472CAA",
                 "confirmed": true,
                 "rejected": false,
                 "has_valid_work": true,
                 "amount": "-10000000000000000000000000000000",
                 "destination": "xrb_1jya8tbffsbsti4hsrjxymwnmuzatq6f6jaigu45z364h6b91qfc6x1nj6bj"
             },
             "status": "success"
         }

   .. group-tab:: Send 10 Mnano (rejected)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> send xrb_1h3h85s4nbuwbcuqxjpprzmsj3reqgfk4i8dzs7otfntff6sqdo9a6deqh3i xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7 "10 mnano"

      .. code-block:: json

         {
             "data": {
                 "hash": "66521D8FFE2C5E63993EDA8E5E2AFF35F2EC9BA993C8751DAE532F439F472CAA",
                 "confirmed": false,
                 "rejected": true,
                 "has_valid_work": true,
                 "amount": "-10000000000000000000000000000000",
                 "destination": "xrb_1jya8tbffsbsti4hsrjxymwnmuzatq6f6jaigu45z364h6b91qfc6x1nj6bj",
                 "error": "block_rejected",
                 "block_error": "fork"
             },
             "message": "At least one block was rejected by the network.",
             "status": "error"
         }

   .. group-tab:: Send 10 Mnano (user-defined timeout)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> send xrb_1h3h85s4nbuwbcuqxjpprzmsj3reqgfk4i8dzs7otfntff6sqdo9a6deqh3i xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7 "10 mnano" --timeout 1

      .. code-block:: json

         {
             "data": {
                 "hash": "66521D8FFE2C5E63993EDA8E5E2AFF35F2EC9BA993C8751DAE532F439F472CAA",
                 "confirmed": false,
                 "rejected": false,
                 "has_valid_work": true,
                 "amount": "-10000000000000000000000000000000",
                 "destination": "xrb_1jya8tbffsbsti4hsrjxymwnmuzatq6f6jaigu45z364h6b91qfc6x1nj6bj",
                 "block_error": "timeout",
                 "error": "network_timeout"
             },
             "message": "The operation could not be finished in the given time.",
             "status": "error"
         }

   .. group-tab:: Send 10 Mnano (txid already exists)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> send xrb_1h3h85s4nbuwbcuqxjpprzmsj3reqgfk4i8dzs7otfntff6sqdo9a6deqh3i xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7 "10 mnano" --txid "important transaction"

      .. code-block:: json

         {
             "data": {
                 "error": "account_already_exists"
             },
             "message": "Account already exists in the wallet",
             "status": "error"
         }

send-many
^^^^^^^^^

Send NANO from one account to another account.

Any rejected blocks won't be saved to the wallet.
Blocks that time out *are* saved into the wallet.

Parameters
""""""""""

- ``source`` (positional) = source account from which NANO is sent
- ``destinations`` (positional, multiple) = one or more ``<destination>,<amount>`` pairs. For ``<amount>``, a single integer can be provided (raw is assumed to be the denomination) or the amount and denomination can be separated with a space.
- ``wait_until_confirmed/no_wait_until_confirmed`` (flag) = whether to wait until the generated blocks are confirmed. Default is true.
- ``description`` (option) = optional description added to every created block.
- ``timeout`` (option) = time to wait in seconds until the blocks are confirmed in the network before giving up. Timeout ignores the time taken to generate PoW. Default is 0, meaning the wallet will wait indefinitely until the blocks are confirmed.

Results
"""""""

.. tabs::

   .. group-tab:: Send 10 Mnano and 5 Mnano

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> send-many xrb_1h3h85s4nbuwbcuqxjpprzmsj3reqgfk4i8dzs7otfntff6sqdo9a6deqh3i "xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7,10 mnano" "xrb_1z4xntxb9gaiyzcfrztkeakxpm9mbrjh8hk3i1igioup84yp5fqfck3eje1k,5000000000000000000000000000000"

      .. code-block:: json

         {
             "data": {
                 "blocks": [
                     {
                         "amount": "-10000000000000000000000000000000",
                         "confirmed": true,
                         "destination": "xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7",
                         "has_valid_work": true,
                         "hash": "0101266AD29C83901E5447E228A8E383B76C8C88DFAA0B202870010E676F40E7",
                         "rejected": false
                     },
                     {
                         "amount": "-5000000000000000000000000000000",
                         "confirmed": true,
                         "destination": "xrb_1z4xntxb9gaiyzcfrztkeakxpm9mbrjh8hk3i1igioup84yp5fqfck3eje1k",
                         "has_valid_work": true,
                         "hash": "4827EA0EEEF1F83E24559544958E7BD185C64A5DA24E5AFE0CC5810FC74E47F7",
                         "rejected": false
                     }
                 ]
             },
             "status": "success"
         }

   .. group-tab:: Send 10 Mnano and 5 Mnano (rejected)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> send-many xrb_1h3h85s4nbuwbcuqxjpprzmsj3reqgfk4i8dzs7otfntff6sqdo9a6deqh3i "xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7,10 mnano" "xrb_1z4xntxb9gaiyzcfrztkeakxpm9mbrjh8hk3i1igioup84yp5fqfck3eje1k,5000000000000000000000000000000"

      .. code-block:: json

         {
             "data": {
                 "blocks": [
                     {
                         "amount": "-10000000000000000000000000000000",
                         "confirmed": true,
                         "destination": "xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7",
                         "has_valid_work": true,
                         "hash": "2C2A249CDD39D958A98C9374C36E55988CF454922A67BA23956FB0177D339C03",
                         "rejected": false
                     },
                     {
                         "amount": "-5000000000000000000000000000000",
                         "block_error": "source_block_missing",
                         "confirmed": false,
                         "destination": "xrb_1z4xntxb9gaiyzcfrztkeakxpm9mbrjh8hk3i1igioup84yp5fqfck3eje1k",
                         "has_valid_work": true,
                         "rejected": true
                     }
                 ],
                 "error": "block_rejected"
             },
             "message": "At least one block was rejected by the network.",
             "status": "error"
         }

   .. group-tab:: Send 10 Mnano and 5 Mnano (user-defined timeout)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> send-many xrb_1h3h85s4nbuwbcuqxjpprzmsj3reqgfk4i8dzs7otfntff6sqdo9a6deqh3i "xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7,10 mnano" "xrb_1z4xntxb9gaiyzcfrztkeakxpm9mbrjh8hk3i1igioup84yp5fqfck3eje1k,5000000000000000000000000000000" --timeout 1

      .. code-block:: json

         {
             "data": {
                 "blocks": [
                     {
                         "amount": "-10000000000000000000000000000000",
                         "confirmed": true,
                         "destination": "xrb_1yf43q8q6j6djmu98kzd8kwzbqdtu1pwffgwbt4jah1qx5kz7yxqx1rghes7",
                         "has_valid_work": true,
                         "hash": "C440E2BEAB88E8C830DA1A9262B20547D862B7EC363208BF30B0DB84FA751EA0",
                         "rejected": false
                     },
                     {
                         "amount": "-5000000000000000000000000000000",
                         "block_error": "timeout",
                         "confirmed": false,
                         "destination": "xrb_1z4xntxb9gaiyzcfrztkeakxpm9mbrjh8hk3i1igioup84yp5fqfck3eje1k",
                         "has_valid_work": true,
                         "hash": "988A230F4CFF30FD49D7EB29BB1E8207700967C28BD48C253BC40DCD048F585B",
                         "rejected": false
                     }
                 ],
                 "error": "network_timeout"
             },
             "message": "The operation could not be finished in the given time.",
             "status": "error"
         }

set-account-name
^^^^^^^^^^^^^^^^

Set a name for an account in the wallet.

Parameters
""""""""""

- ``account_id`` (positional) = account ID of the account
- ``name`` (positional) = name to set for the account

Results
"""""""

.. tabs::

   .. group-tab:: Set description

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> set-account-name xrb_1qrb86ngd4aqe7n9s4xqrhu5tmxb7mph6kp46qz9xhmg8keomgsemmsrwsep "Savings"

      .. code-block:: json

         {
             "data": {
                 "account_id": "xrb_1qrb86ngd4aqe7n9s4xqrhu5tmxb7mph6kp46qz9xhmg8keomgsemmsrwsep",
                 "name": "Savings"
             },
             "status": "success"
         }

   .. group-tab:: Account not found

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> set-account-name xrb_1qrb86ngd4aqe7n9s4xqrhu5tmxb7mph6kp46qz9xhmg8keomgsemmsrwsep "Savings"

      .. code-block:: json

         {
             "data": {
                 "error": "account_not_found"
             },
             "message": "Account not found in the wallet",
             "status": "error"
         }

set-block-description
^^^^^^^^^^^^^^^^^^^^^

Set a block description for a given block by its block hash.

Pocketed blocks can't be given descriptions.

Parameters
""""""""""

- ``block_hash`` (positional) = block hash for the block
- ``description`` (positional) = description to add

Results
"""""""

.. tabs::

   .. group-tab:: Set description

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> set-block-description 6C659CECE6B30323B3A3D4CD2B8C6BA1A16D8CF931379A58F5D97055D06FE1A7 "Bob's deposit"

      .. code-block:: json

         {
             "data": {
                 "account_id": "nano_3u7d5iohy14swyhxhgfm9iq4xa9yibhcgnyj697uwhicp14dhx4woik5e9ek",
                 "description": "Bob's deposit",
                 "hash": "6C659CECE6B30323B3A3D4CD2B8C6BA1A16D8CF931379A58F5D97055D06FE1A7"
             },
             "status": "success"
         }

   .. group-tab:: Block not found

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> set-block-description 6C659CECE6B30323B3A3D4CD2B8C6BA1A16D8CF931379A58F5D97055D06FE1A7 "Bob's deposit"

      .. code-block:: json

         {
             "data": {
                 "error": "block_not_found"
             },
             "message": "Block not found in the wallet",
             "status": "error"
         }

sync
^^^^

Synchronize the wallet with the network.

Pocketable blocks will be received and PoW generated to receive the NANO.

.. note::

   If one of the accounts in your account is constantly receiving pocketable blocks, it is best to use ``--no-finish-work`` and ``--no-finish-sync`` flags.
   Otherwise, the command may block forever as the account never finishes pocketing NANO it keeps receiving.

Parameters
""""""""""

- ``finish_work/no_finish_work`` (flag) = postpone timeout until all pending PoW have been generated. Enabled by default.
- ``finish_sync/no_finish_sync`` (flag) = postpone timeout until blockchains for all the accounts have been synchronized. This means completing the blockchain and pocketing any received blocks. Enabled by default.
- ``timeout`` (option) = timeout in seconds until the command will return a result. Default is 10 seconds.
- ``result_count`` (option) = how many results to return at most per category (new, rejected, received). Default is 50.

Results
"""""""

.. tabs::

   .. group-tab:: Synchronize

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> sync

      .. code-block:: json

         {
             "data": {
                 "new_blocks": {
                     "xrb_1m59yfcuo3jko3qm493hipxynczixjezmopyyayueobrmowyrq7po5ewjdte": [
                         {
                             "block_data": {
                                 "account": "xrb_1m59yfcuo3jko3qm493hipxynczixjezmopyyayueobrmowyrq7po5ewjdte",
                                 "balance": "4000",
                                 "link": "972630520662B2174555BDDBEC831134EF3612ABCDCF9EB8AB8C339140B943C1",
                                 "link_as_account": "xrb_37s883b1erok4x4odhguxk3j4f9h8rbcqmghmtwcq53mk71dkiy345j16r1j",
                                 "previous": "0000000000000000000000000000000000000000000000000000000000000000",
                                 "representative": "xrb_1111111111111111111111111111111111111111111111111111hifc8npp",
                                 "signature": "579A3DE99FFFCF1908954FEB108586C6175EFC0BD852EF88B95F7F4317211CEC116FCEF95612BFAB2AA3DCCB2B9BB23EA13C845CAC9F723BAFF8DC9EC3B5650D",
                                 "type": "state",
                                 "work": "77493c713693ac53"
                             },
                             "hash": "53E585FD8672C8F134464A6A18AD06BE714AE9BDDB5E2DC3F266D36F33B68359",
                             "tx_type": "open"
                         }
                     ],
                     "xrb_3d956ototgofcrsdyy86a8n6cyrcygc1g5ipqh6w7kno1jrdzeh48r6d5de1": [
                         {
                             "block_data": {
                                 "account": "xrb_3d956ototgofcrsdyy86a8n6cyrcygc1g5ipqh6w7kno1jrdzeh48r6d5de1",
                                 "balance": "12000",
                                 "link": "65613897FBA91E172DDF1FA2CCE66B003B48F4B4F269FF83F5839915DD46AFC8",
                                 "link_as_account": "xrb_1sd394dzqcay4wpxy9x4smm8p13ub5tdbwmbzy3zd1ws4qgnfdya4jyewmsm",
                                 "previous": "511925119B6FE682911171657F93B21ADEA80F4B180D4654454816B7E8A28FD7",
                                 "representative": "xrb_1111111111111111111111111111111111111111111111111111hifc8npp",
                                 "signature": "298B26DB618E2BC08C753DE6D082071AD8F8C364F97B71D15F699CC32815E7016BC97BF28763A0370145498574A2531B3A7B4596D5B68DA24DABD64E0ED7E305",
                                 "type": "state",
                                 "work": "8cfc10b41127d52d"
                             },
                             "hash": "B155DB2809FA21566E67BA2A3BB526ED20366A858516C17A730A8AD5BA4202D1",
                             "tx_type": "receive"
                         }
                     ]
                 },
                 "received_blocks": {
                     "xrb_1m59yfcuo3jko3qm493hipxynczixjezmopyyayueobrmowyrq7po5ewjdte": [
                         {
                             "amount": "4000",
                             "hash": "972630520662B2174555BDDBEC831134EF3612ABCDCF9EB8AB8C339140B943C1",
                             "source": "xrb_3yamaos3ssnk1m1fd59dme658axd5su4o8qxe8in9rn97hrgbcxs6nastiie"
                         }
                     ],
                     "xrb_3d956ototgofcrsdyy86a8n6cyrcygc1g5ipqh6w7kno1jrdzeh48r6d5de1": [
                         {
                             "amount": "2000",
                             "hash": "65613897FBA91E172DDF1FA2CCE66B003B48F4B4F269FF83F5839915DD46AFC8",
                             "source": "xrb_18miazfii3nmp3g78x5d1y6r33wwntutzusfjcsbtu1rtptxxgjfqtfwfzws"
                         }
                     ]
                 },
                 "rejected_blocks": {}
             },
             "status": "success"
         }

   .. group-tab:: Synchronize (with rejected blocks)

      .. code-block:: console

         $ siliqua --wallet <WALLET PATH> sync

      .. code-block:: json

         {
             "data": {
                 "error": "block_rejected",
                 "new_blocks": {},
                 "received_blocks": {},
                 "rejected_blocks": {
                     "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc": [
                         {
                             "block_error": "previous_block_missing",
                             "data": {
                                 "account": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                                 "balance": "0",
                                 "link": "0000000000000000000000000000000000000000000000000000000000000000",
                                 "link_as_account": "xrb_1111111111111111111111111111111111111111111111111111hifc8npp",
                                 "previous": "96970559D7257F63ACB8383ED57CB510745DE744ABCEC4DC41590CE7E32179EA",
                                 "representative": "xrb_1nanoftwk6741wmdznzangwm8prq95spu3zntb5gwpjdk8qd3p8eu5bxoehc",
                                 "signature": "BBC27F177C2C2DD574AE8EB8523A1A504B5790C65C95ACE744E3033A63BB158DDF95F9B7B88B902C8D743A64EA25785662CD454044E9C3000BC79C3BF7F1E809",
                                 "type": "state",
                                 "work": "561bab16393cb3c4"
                             },
                             "hash": "62EE070DA06632FE1E54BA32FD25B00A5FD4E8CF09354A9B176CBF6BC33CDBDB"
                         }
                     ]
                 }
             },
             "message": "At least one block was rejected by the network.",
             "status": "error"
         }

Pagination parameters
---------------------

Some of the commands accept pagination parameters. This allows the
results to be controlled with three parameters:

- ``limit`` (option) = how many results to return at most
- ``offset`` (option) = how many results to skip. Defaults to 0.
- ``descending/no_descending`` (flag) = whether to return results in a descending order (newest to oldest).

The result will also report the total number of entries available for pagination in the ``count`` field.

.. _JSend: https://github.com/omniti-labs/jsend

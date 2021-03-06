# template: github.com/threefoldtoken/0-templates/block_creator/0.0.2

### Description:
This template is responsible for deploying block creator node.

### Schema:

- `rpcPort`: rpc port for the deamon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `walletSeed`: wallet's primary seed, should be set at start
- `walletPassphrase`: wallet passphrase, if omitted, one will be generated
- `walletAddr`: address of the wallet
- `network`: network to join, default standard
- `ethbootnodes`: Custom ethereum bootnodes to connect to at startup
- `tfchainFlist`: the flist to be used for the tfchain (default: https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-tfchain-autostart-master.flist)


### Actions
- `install`: prepare persistent volume
- `uninstall`: remove persistent volume
- `upgrade`: update the service
- `start`: starts the container and the tfchain daemon process and init wallet.
- `stop`: stops the tfchain daemon process.
- `wallet_address`: return wallet address
- `wallet_amount`: return the amount of token in the wallet
- `consensus_stat`: return some statistics about the consensus

### Examples:

#### DSL (api interface):

```python
data = {'node':'node1'}
bc = robot.services.create('github.com/threefoldfoundation/tfchain-templates/block_creator/0.0.2','block_creator', data)
bc.schedule_action('install')
bc.schedule_action('start')
```

#### Blueprint (cli interface):

```yaml
services:
    - github.com/threefoldtoken/0-templates/block_creator/0.0.2__block_creator:
        node: node1

actions:
    - actions: ['install','start']
      service: block_creator
```

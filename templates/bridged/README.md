# template: github.com/threefoldtoken/0-templates/bridged/0.0.2

### Description:
This template is responsible for deploying bridged daemon.

### Schema:

- `rpcPort`: rpc port for the deamon (default 23112)
- `node`: reference to the node running the tfchain container
- `ethPort`: etherum port (default 3003)
- `walletSeed`: wallet's primary seed, should be set at start
- `walletPassphrase`: wallet passphrase, if omitted, one will be generated
- `walletAddr`: address of the wallet
- `network`: network to join, default standard
- `ethbootnodes`: Custom ethereum bootnodes to connect to at startup
- `bridgedFlist`: the flist to be used for the bridged (default: https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-bridged-autostart-master.flist)


### Actions
- `install`: prepare persistent volume
- `uninstall`: remove persistent volume
- `upgrade`: update the service with new flist
- `start`: starts the container and the bridged daemon
- `stop`: stops the bridged container


### Examples:

#### DSL (api interface):

```python
BRIDGED_ID = 'github.com/threefoldfoundation/tfchain-templates/bridged/0.0.2'

b = r.services.create(BRIDGED_ID, 'b16', {'node': 'local', 'network':'testnet', 'ethPort':3003} )  
b.schedule_action('install')
b.schedule_action('start')
```

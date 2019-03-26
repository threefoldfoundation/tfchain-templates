# template: github.com/threefoldtoken/0-templates/explorer/0.0.2

## Description

This template is responsible for deploying an explorer node.

## Schema

- `rpcPort`: rpc port for the daemon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `domain`: domain name where to expose the explorer web page
- `network`: network to join, default standard
- `explorerFlist`: the flist to be used for the explorer (default: https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-explorer-autostart-master.flist)
- `walletSeed`: wallet's primary seed, should be set at start
- `walletPassphrase`: wallet passphrase, if omitted, one will be generated
- `walletAddr`: address of the wallet
- `ethbootnodes`: Custom ethereum bootnodes to connect to at startup


## Actions

- `install`: prepare persistent volume
- `uninstall`: remove persistent volume
- `upgrade`: update the service
- `start`: starts the container and the explorer daemon process and init wallet.
- `stop`: stops the explorer daemon container.


## Examples

### DSL (api interface)

```python
EXPLORER_ID =  'github.com/threefoldfoundation/tfchain-templates/explorer/0.0.2'
explorer = robot.services.create(EXPLORER_ID, 'e1', {'node': 'local','domain':'coolcoin', 'ne
      ...: twork':'devnet'} ) 
explorer.schedule_action('install')
explorer.schedule_action('start')
```


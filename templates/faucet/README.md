# template: github.com/threefoldfoundation/tfchain-templates/faucet/0.0.2

## Description

This template is responsible for deploying a faucet.

## Schema

- `rpcPort`: rpc port for the daemon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `domain`: domain name where to expose the explorer web page
- `network`: network to join, default testnet
- `faucetFlist`: the flist to be used for the faucet (default: https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-faucet-autostart-master.flistt)

- `walletSeed`: seed of the wallet, if not set one is generated
- `walletPassphrase`: password for the wallet, if not set one is generated
- `walletAddr`: address of the wallet

## Actions

- `install`: prepare persistent volume
- `uninstall`: remove persistent volume
- `upgrade`: update the service
- `start`: starts the container and the tfchain daemon process and init wallet, start faucet.
- `stop`: stops the tfchain daemon process and faucet.


## Examples

### DSL (api interface)

```python
FAUCET_ID =  'github.com/threefoldfoundation/tfchain-templates/faucet/0.0.2'  
f = robot.services.create(FAUCET_ID, 'f1', {'node': 'local','domain':'coolcoin', 'network':'devnet'} )
faucet.schedule_action('install')
faucet.schedule_action('start')
```


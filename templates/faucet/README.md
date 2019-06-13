# template: github.com/threefoldfoundation/tfchain-templates/faucet/0.0.1

## Description

This template is responsible for deploying a faucet.

## Schema

- `rpcPort`: rpc port for the daemon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `domain`: domain name where to expose the explorer web page
- `network`: network to join, default testnet
- `tfchainFlist`: the flist to be used for the tfchain (default: https://hub.grid.tf/tfchain/ubuntu-16.04-tfchain-edge.flist)
- `faucetFlist`: the flist to be used for the faucet (default: https://hub.grid.tf/tfchain/caddy-faucet.flist)
- `macAddress`: mac address for the macvlan interface (optional)
- `parentInterface`: parent interface for macvlan, if not set then discovered automatically (optional)
- `walletSeed`: seed of the wallet, if not set one is generated
- `walletPassphrate`: password for the wallet, if not set one is generated
- `walletAddr`: address of the wallet

## Actions

- `install`: create container with tfchain binaries.
- `start`: starts the container and the tfchain daemon process and init wallet, start faucet.
- `stop`: stops the tfchain daemon process and faucet.
- `consensus_stat`: return some statistics about the consensus.
- `gateway_stat`: return some statistics about the gateway.

## Examples

### DSL (api interface)

```python
data = {'node':'local', 'domain': 'faucet.tft.com'}
explorer = robot.services.create('github.com/threefoldfoundation/tfchain-templates/faucet/0.0.1','faucet', data)
explorer.schedule_action('install')
explorer.schedule_action('start')
```


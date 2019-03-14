# template: github.com/threefoldfoundation/tfchain-templates/geth/0.0.2

## Description

This template is responsible for deploying a geth node.

## Schema

- `network`: Ethereum network ("testnet" (=ropsten) or "rinkeby" or ("" for production network)) (default testnet)
- `v5disc`: Enables the experimental RLPx V5 (Topic Discovery) mechanism (default: 'v5disc')
- `lightserv`: Maximum percentage of time allowed for serving LES requests (0-90) (default: 90)
- `syncmode`: Blockchain sync mode ("fast", "full", or "light") (default: "full")
- `nat`: NAT port mapping mechanism (any|none|upnp|pmp|extip:<IP>) (default: "any")
- `verbosity`: Logging verbosity: 0=silent, 1=error, 2=warn, 3=info, 4=debug, 5=detail (default: 4)
- `ethport`: Etherum port (default 30303)
- `gethFlist`: the flist to be used for the geth (default: https://hub.grid.tf/tf-official-apps/geth.flist)

## Actions

- `install`: prepare persistent volume
- `uninstall`: remove persistent volume
- `upgrade`: update the service
- `start`: starts the container.
- `stop`: stops the geth process.
- `getSyncingStatus`: gets the ethereum syncing progress, returns [currentblock, highestblock]

## Examples

### DSL (api interface)

```python
GETH_ID =  'github.com/threefoldfoundation/tfchain-templates/geth/0.0.2'  
f = robot.services.create(GETH_ID, 'geth', {'network':'testnet', 'v5disc':'v5disc', 'lightserv':'90', 'ethport': '30303'} )
geth.schedule_action('install')
geth.schedule_action('start')
```

## Enode address for geth node

To retrieve the enode address for your running geth node:

```python
task = serv.schedule_action("get_enode_address").wait()  
enode_address = task.result
```


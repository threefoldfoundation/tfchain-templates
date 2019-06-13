@0xb96c7457b3a2bc76;

struct Schema {
    node @0: Text;                # reference to the node running the tfchain container
    rpcPort @1: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @2: UInt32=23110;     # http port for tfchain client
    domain @3: Text; # domain name where to expose the faucet web page
    network @4: Text="testnet"; # network to join
    tfchainFlist @5: Text="https://hub.grid.tf/tfchain/ubuntu-16.04-tfchain-edge.flist"; # flist to use for tfchain
    faucetFlist @6: Text="https://hub.grid.tf/tfchain/caddy-faucet.flist"; # flist to use for the faucet
    macAddress @7: Text; # mac address for the macvlan interface
    parentInterface @8: Text="";     # parent interface for macvlan, if not set then discovered automatically
    walletSeed @9: Text;	# seed for the wallet, if not set one is generated
    walletPassphrase @10: Text;	# password for the wallet, if not set one is generated
    walletAddr @11: Text;	# address of the wallet
}

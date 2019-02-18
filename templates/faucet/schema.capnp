@0xb96c7457b3a2bc76;

struct Schema {
    node @0: Text;                # reference to the node running the tfchain container
    rpcPort @1: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @2: UInt32=23110;     # http port for tfchain client
    domain @3: Text; # domain name where to expose the faucet web page
    network @4: Text="testnet"; # network to join
    faucetFlist @5: Text="https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-faucet-autostart-master.flist"; # flist to use for the faucet
    walletSeed @6: Text;	# seed for the wallet, if not set one is generated
    walletPassphrase @7: Text;	# password for the wallet, if not set one is generated
    walletAddr @8: Text;	# address of the wallet
    faucetPort @9: UInt32 = 8080; # port to run tftfaucet on
}

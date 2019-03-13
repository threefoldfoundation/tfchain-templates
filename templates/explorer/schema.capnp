@0xe6641479f7821354;

struct Schema {
    node @0: Text;                # reference to the node running the tfchain container
    rpcPort @1: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @2: UInt32=23110;     # http port for tfchain client
    domain @3: Text; # domain name where to expose the explorer web page
    network @4: Text="standard"; # network to join
    explorerFlist @5: Text="https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-explorer-autostart-master.flist"; # flist to use for explorer
    walletSeed @6: Text;
    walletPassphrase @7: Text;
    # address of the wallet
    walletAddr @8: Text;
    ethbootnodes @9: Text;
}

@0xa8a6181651fd405c;

struct Schema {
    # reference to the node running the tfchain container    
    node @0: Text;
    
    # rpc port of tfchain daemon
    rpcPort @1: UInt32=23112;
    
    # http port for tfchain client
    apiPort @2: UInt32=23110;
    
    walletSeed @3: Text;
    
    walletPassphrase @4: Text;

    # address of the wallet
    walletAddr @5: Text;

    # network to join
    network @6: Text="standard";

    # ethereum bootnodes
    ethbootnodes @7: Text;

    # flist to use for tfchain
    tfchainFlist @8: Text="https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-tfchain-autostart-master.flist";

}

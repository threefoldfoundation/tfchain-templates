@0xba1805e2bd8cb67b;

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

    # flist to use for tfchain
    tfchainFlist @7: Text="https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-bridge_tft_erc20_autostart.flist";
 
    # parent interface for macvlan, if not set then discovered automatically
    parentInterface @8: Text=""; 

    # mac address for the macvlan interface
    macAddress @9: Text=""; 

    # bridged server rpc port
    bridgedRpcPort @10: UInt32;

    # etherum network
    ethNetwork @11: Text;

    # etherum port
    ethPort @12: UInt32;

    # etherum account json
    ethAccountJson @13: Text;

    # etherum account password
    ethAccountPassword @14: Text;
}

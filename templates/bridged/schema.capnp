@0xfc6d822cb69e2d25;


struct Schema {
    # reference to the node running the tfchain container    
    node @0: Text;
    rpcPort @1: UInt32;
    network @2: Text;
    ethPort @3: UInt32=3003; 
    accountJson @4: Text;
    accountPassword @5: Text;
    # autostart flist for bridged
    bridgedFlist @6: Text="https://hub.grid.tf/tf-autobuilder/threefoldfoundation-tfchain-bridged-autostart-master.flist";

}

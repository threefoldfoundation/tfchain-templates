@0xd8f961de7be52fef;

struct Schema {
    # reference to the node running the tfchain container    
    node @0: Text;
    coredns3botFlist @1: Text="https://hub.grid.tf/tf-autobuilder/threefoldtech-threebot_coredns-threebot_coredns-autostart-master.flist";
    zone      @2: Text;
    explorers @3: List(Text);
}

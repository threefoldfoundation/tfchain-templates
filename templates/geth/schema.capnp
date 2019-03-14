@0xb96c7457b3a2bc76;

struct Schema {
    network @0: Text="testnet"; # ethereum network preference, 'testnet', 'rinkeby', ..'
    lightserv @1: UInt32=90;     # ethereum lightserv
    verbosity @2: UInt32=4;     # ethereum logging
    v5disc @3: Text; # ethereum v5disc packets
    syncmode @4: Text="full"; # ethereum network syncmode, 'full', 'fast', ..
    nat @5: Text="none"; # ethereum natmode, 'none', ..
    datadir @6: Text="/mnt/data"; # ethereum datadir
    ethport @7: UInt32=30303; # ethereum port
    gethFlist @8: Text="https://hub.grid.tf/tf-official-apps/geth.flist"; # flist to use for geth
}

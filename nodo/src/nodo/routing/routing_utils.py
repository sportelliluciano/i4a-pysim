def get_node_subnets(network, mask):
    prefix_len = mask.bit_count() + 3
    new_mask = ((1 << prefix_len) - 1) << (32 - prefix_len)
    node_networks = {}
    for assigned_block in range(1, 6):
        new_network = network | (assigned_block << (32 - new_mask.bit_count()))
        node_networks[assigned_block] = new_network
    return node_networks, new_mask

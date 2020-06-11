'''
I/O methods for neighbor files and node map files
'''

import codecs

def writeNodeMap(emb, f):
    ordered = tuple([
        k.strip()
            for k in emb.keys()
            if len(k.strip()) > 0
    ])
    node_id = 1  # start from 1 in case 0 is reserved in node2vec
    with codecs.open(f, 'w', 'utf-8') as stream:
        for v in ordered:
            stream.write('%d\t%s\n' % (
                node_id, v
            ))
            node_id += 1
    
def readNodeMap(f, as_ordered_list=False):
    node_map = {}
    with codecs.open(f, 'r', 'utf-8') as stream:
        for line in stream:
            (node_id, v) = [s.strip() for s in line.split('\t')]
            node_map[int(node_id)] = v

    if as_ordered_list:
        keys = list(node_map.keys())
        keys.sort()
        node_map = [
            node_map[k]
                for k in keys
        ]
    return node_map

def writeNeighborFileLine(stream, node_ID, neighbors, with_distances=False):
    if with_distances:
        neighbor_info = [
            '%s||%.6f' % (
                str(d), dist
            )
                for (d, dist) in neighbors
        ]
    else:
        neighbor_info = neighbors
    stream.write('%s\n' % ','.join([
        str(d) for d in [
            node_ID, *neighbor_info
        ]
    ]))

def readNeighborFile(f, k=None, node_map=None, with_distances=False, query_node_map=None):
    '''Read a neighbor file into a dictionary mapping
    { node: [neighbor list] }

    If k is supplied, restricts to the first k neighbors
    listed (i.e., the closest k neighbors)

    If node_map is supplied (as a dict), maps node IDs
    to labels in node_map.
    '''
    neighbors = {}

    if node_map:
        remap = lambda key: node_map.get(key, key)
        if query_node_map:
            query_remap = lambda key: query_node_map.get(key, key)
        else: query_remap = remap
    else:
        remap = lambda key: key
        query_remap = remap

    with codecs.open(f, 'r', 'utf-8') as stream:
        for line in stream:
            if line[0] != '#':
                (node_ID, *neighbor_info_strs) = line.split(',')
                node_ID = query_remap(int(node_ID))
                if with_distances:
                    neighbor_info = []
                    for nbr_info in neighbor_info_strs:
                        nbr_ID, dist = nbr_info.split('||')
                        neighbor_info.append((
                            remap(int(nbr_ID)), float(dist)
                        ))
                else:
                    neighbor_info = [
                        remap(int(nbr_ID))
                            for nbr_ID in neighbor_info
                   ]
                if k:
                    neighbor_info = neighbor_info[:k]
                neighbors[node_ID] = neighbor_info
    return neighbors

def readStringMap(f, lower_keys=False):
    _map = {}
    with open(f, 'r') as stream:
        for line in stream:
            (ID, string) = [s.strip() for s in line.split('\t')]
            if lower_keys: ID = ID.lower()
            _map[ID] = string
    return _map

def readSet(f, to_lower=False):
    _set = set()
    with open(f, 'r') as stream:
        for line in stream:
            line = line.strip()
            if to_lower: line = line.lower()
            _set.add(line)
    return _set

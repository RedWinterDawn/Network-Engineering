from heapq import heappush, heappop
from itertools import count

def single_source_dijkstra_rr(G, source, target=None, cutoff=None, weight='weight'):
    """
        A minor edit to the dijkstra code from networkx to record the route that
        has been taken through the network for a multigraph

        Uses the attribute 'key' to determine the name of the link.
    """
    if source == target:
        return ({source: 0}, {source: [source]})
    push = heappush
    pop = heappop
    dist = {}  # dictionary of final distances
    paths = {source: {'path': [[source]], 'route': [[]]}}  # dictionary of paths
    record_route = {source: []}
    seen = {source: 0}
    c = count()
    fringe = []  # use heapq with (distance,label) tuples
    push(fringe, (0, next(c), source))
    while fringe:
        (d, _, v) = pop(fringe)
        if v in dist:
            continue  # already searched this node.
        dist[v] = d
        if v == target:
            break
        # for ignore,w,edgedata in G.edges_iter(v,data=True):
        # is about 30% slower than the following
        if G.is_multigraph():
            edata = []
            for w, keydata in G[v].items():
                minweight = min((dd.get(weight, 1)
                                 for k, dd in keydata.items()))
                # record the links that were part of this shortest
                # path (rather than solely the minweight)
                spf = []
                for k, dd in keydata.items():
                    if dd.get(weight, 1) == minweight:
                        spf.append((v,w,k,minweight))
                edata.append((w, {weight: minweight, 'path': spf}))
        else:
            edata = iter(G[v].items())

        for w, edgedata in edata:
            vw_dist = dist[v] + edgedata.get(weight, 1)
            if cutoff is not None:
                if vw_dist > cutoff:
                    continue
            if w in dist:
                if vw_dist < dist[w]:
                    raise ValueError('Contradictory paths found:',
                                     'negative weights?')
            elif w not in seen or vw_dist <= seen[w]:
                # determine whether this was a new bestpath, or whether
                # it is an equal cost bestpath.
                new_bestpath = True if w in seen and vw_dist < seen[w] else False
                seen[w] = vw_dist
                push(fringe, (vw_dist, next(c), w))
                # if this is a new path, or are replacing the bestpath
                # then re-initialise the storage of paths.
                if not w in paths or new_bestpath:
                    paths[w] = {'path': [], 'route': []}
                # append the node to the recorded path
                for i in paths[v]['path']:
                    paths[w]['path'].append((i+[w]))
                # append the routes to the path
                rt = edgedata.get('path')
                if len(rt) > 1:
                    rt = [rt]
                for i in paths[v]['route']:
                    paths[w]['route'].append(i+rt)
    return (dist, paths)

def all_pairs_dijkstra_path_rr(G, cutoff=None, weight='weight'):
    paths = {}
    for n in G:
        paths[n] = single_source_dijkstra_rr(G, n, cutoff=cutoff, weight=weight)
    return paths
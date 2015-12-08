#!/usr/bin/env python

import sys
import re
import jneteng.multigraph as multigraph
import jneteng.spt_helper as spt_helper
import jneteng.topology as topology

VPLS_BASE_COST = 100
DMVPN_BASE_COST = 300

DISTANCE_MATRIX_PATH = "data/datacentre-distance-matrix.csv"
NODE_DICTIONARY_PATH = "data/datacentre-info.csv"
LINK_OUTPUT_PATH = "data/link-list.csv"

network = topology.build_topology(DISTANCE_MATRIX_PATH, NODE_DICTIONARY_PATH, VPLS_BASE_COST, DMVPN_BASE_COST, LINK_OUTPUT_PATH=LINK_OUTPUT_PATH)

G = network['graph']
added = network['link_dict']

# base topology - expect all nodes with DMVPN to be routing via DMVPN
nofailures = spt_helper.shortest_path_class(G)

for a in nofailures:
  for b in nofailures[a]:
    # check that there is only one a->b path
    assert nofailures[a][b]['ecmp_count'] == 1, \
      "ERROR: %s->%s has an invalid path, multiple (%d) ECMPs available" % (a, b, nofailures[a][b]['ecmp_count'])
    if G.node[a]['attr']['vpls'] and G.node[b]['attr']['vpls']:
      # check that the one path is over VPLS if the nodes have VPLS
      assert nofailures[a][b]['ecmps'][0] == (1, ["VPLS"]), \
        "ERROR: %s->%s has an invalid path, does not traverse VPLS [%s]" % (a, b, nofailures[a][b]['ecmps'][0])
    else:
      # check that teh one path is over DMVPN
      assert nofailures[a][b]['ecmps'][0] == (1, ["DMVPN"]), \
        "ERROR: %s->%s has an invalid path, multihop! [%s]" % (a,b, nofailures[a][b]['ecmps'][0])

# fail each node's VPLS connections one by one
for n in G:
  if G.node[n]['attr']['vpls']:
    down_links = spt_helper.fail_links(G, n, link_class='VPLS')
    new_spt = spt_helper.shortest_path_class(G)
    for a in new_spt:
      for b in new_spt[a]:
        # everything should still be one ECMP
        assert new_spt[a][b]['ecmp_count'] == 1, \
          "ERROR: %s->%s has an invalid path, multiple (%d) ECMPs available" % (a, b, new_spt[a][b]['ecmp_count'])
        if a == n or b == n:
          # we expect that this path has changed, everything should be one-hop over DMVPN
          assert new_spt[a][b]['ecmps'][0] == (1,["DMVPN"]), \
            "ERROR: %s->%s (failures for %s) should be 1-hop over DMVPN [%s]" % (n,a,b,new_spt[a][b]['ecmps'][0])
        else:
          # expected behaviour: direct DMVPN if the other node does not have VPLS, otherwise, multihop
          # one on VPLS on DMVPN
          if G.node[a]['attr']['vpls'] and G.node[b]['attr']['vpls']:
            assert new_spt[a][b]['ecmps'][0] == (1, ["VPLS"]), \
              "ERROR: %s->%s should not have changed path, should remain on VPLS [%s]" % (a,b,new_spt[a][b]['ecmps'][0])
          else:
            assert new_spt[a][b]['ecmps'][0] == (1,["DMVPN"]), \
              "ERROR: %s->%s should not have changed path, should be single-hop on DMVPN [%s]" % (a,b,new_spt[a][b]['ecmps'][0])
    spt_helper.up_links(G, down_links)

# work through and fail each DMVPN connection, check SPT tree only has two hops for the
# nodes with failed tunnels
# do this first with all VPLS links up.
for a in G:
  for b in G:
    if a == b:
      continue
    down_links = spt_helper.fail_links(G,a,specific_link=(a,b, "%s-dmvpn" % added[a][b]))
    new_spt = spt_helper.shortest_path_class(G)
    for x in new_spt:
      for y in new_spt:
        if x == y:
          continue
        x_end_spt = multigraph.single_source_dijkstra_rr(G, x, weight='metric')
        if not new_spt[x][y]['ecmp_count'] == 1:
          sys.stderr.write("INFO %s->%s (during failures of %s->%s - with VPLS): Had multiple (%d) ECMPs\n" \
            % (x, y, a, b, new_spt[x][y]['ecmp_count']))
          c = 0
          for route in x_end_spt[1][y]['route']:
            #info_str = "INFO %s->%s (during failures of %s->%s - with VPLS): Path %d - " % (x, y, a, b, c)
            info_str = "\t\tPath %d: " % c
            for link in route:
              info_str += "%s (%d) - " % (link[2], link[3])
            c += 1
            info_str = re.sub('[ \-]+$', '', info_str)
            sys.stderr.write(info_str+"\n")
        for pth in new_spt[x][y]['ecmps']:
          # if both nodes have VPLS, then we should remain on it
          if G.node[x]['attr']['vpls'] and G.node[y]['attr']['vpls']:
            assert pth == (1,["VPLS"]), \
              "ERROR: %s->%s should not have changed path and remained on VPLS [%s]" % (x,y,pth)
          # else, if we were not involved in the failure, one-hop DMVPN
          else:
            if x in [a,b] and y in [a,b]:
              # nodes were involved in failure, and only has DMVPN, should be a two-hop VPLS+DMVPN or
              # two-hop DMVPN

              this_path = x_end_spt[1][y]
              if G.node[x]['attr']['vpls']:
                assert pth == (2,["VPLS","DMVPN"]), \
                  "ERROR: %s->%s did not become a two-hop path that was VPLS+DMVPN when %s->%s failed [%s, %s]" % \
                    (x,y,a,b,pth,this_path)
              elif G.node[y]['attr']['vpls']:
                # it is only acceptable to do a DMVPN hop and then a VPLS one when there is no local VPLS and the remote device has
                # VPLS
                assert pth == (2,["DMVPN", "VPLS"]), \
                  "ERROR: %s->%s did not become a two-hop path that was DMVPN+VPLS when %s->%s failed [%s, %s]" % \
                    (x,y,a,b,pth,this_path)
              else:
                # neither end has VPLS, so we must do 2*DMVPN
                assert pth == (2,["DMVPN","DMVPN"]), \
                  "ERROR: %s->%s did not become a two-hop path that was DMVPN-only when %s->%s failed [%s, %s]" % \
                    (x,y,a,b,pth,this_path)

            else:
              assert pth == (1,["DMVPN"]), \
                "ERROR: %s->%s should not have changed path and remained on DMVPN (%s->%s failed) [%s]" % \
                  (x,y,a,b,pth)
    spt_helper.up_links(G, down_links)

# and now fail the VPLS links at that site if it has them
for a in G:
  if G.node[a]['attr']['vpls']:
    failed_vpls = spt_helper.fail_links(G, a, link_class="VPLS")
  else:
    # no point running this simulation, because nothing has changed
    # c.f. the above
    continue
  for b in G:
    if a == b:
      continue
    down_links = spt_helper.fail_links(G, a, specific_link=(a,b,"%s-dmvpn" % added[a][b]))
    new_spt = spt_helper.shortest_path_class(G)
    for x in new_spt:
      for y in new_spt[x]:
        if x == y:
          continue
        x_end_spt = multigraph.single_source_dijkstra_rr(G, x, weight='metric')
        if not new_spt[x][y]['ecmp_count'] == 1:
          sys.stderr.write("INFO %s->%s (during failures of %s->%s with %s VPLS failed: Had multiple ECMPs (%s)\n" % \
            (x, y, a, b, a, new_spt[x][y]['ecmp_count']))
          c = 0
          for route in x_end_spt[1][y]['route']:
            #info_str = "INFO %s->%s (during failures of %s->%s with %s VPLS failed: Path %d -" % (x, y, a, b, a, c)
            info_str = "\t\tPath %d: " % c
            for link in route:
              info_str += "%s (%d) - " % (link[2], link[3])
            c += 1
            info_str = re.sub('[ \-]+$', '', info_str)
            sys.stderr.write(info_str + "\n")

        # if x has a VPLS failure
          # route should be DMVPN, VPLS if the remote node has VPLS
          # else it should be DMVPN
        # if y has a VPLS failure
          # route should be VPLS, DMVPN if the local node has VPLS
          # else it should be DMVPN
        # if neither has a VPLS failure
          # if VPLS if both nodes have VPLS
          # else
          # if x and y are involved in the DMVPN failure
            # if x does not have VPLS, and y does: should be DMVPN,VPLS
            # if y does not have VPLS, and x does: should be VPLS,DMVPN
            # if neither has vpls: should be DMVPN,DMVPN

        for pth in new_spt[x][y]['ecmps']:
          check_vpls = False
          if x == a:
            if x in [a,b] and y in [a,b]:
              # this pair also has the DMVPN failure
              if G.node[y]['attr']['vpls']:
                assert pth == (2, ["DMVPN", "VPLS"]), \
                  "ERROR: %s->%s during failure of %s VPLS and %s->%s - should be DMVPN, VPLS [%s]" % \
                    (a, b, a, a, b, pth)
              else:
                assert pth == (2, ["DMVPN", "DMVPN"]), \
                  "ERROR: %s->%s during failure of %s VPLS and %s->%s - should be 2-hop DMVPN [%s]" % \
                    (a, b, a, a, b, pth)
            else:
              # this pair doesn't have a DMVPN failure too, so we should
              # be able to one-hop over DMVPN
              assert pth == (1, ["DMVPN"]), \
                "ERROR: %s->%s during failure of %s VPLS and %s->%s should be straight DMVPN [%s]" % \
                  (a, b, a, a, b, pth)

          elif y == a:
            if x in [a,b] and y in [a,b]:
              if G.node[x]['attr']['vpls']:
                assert pth == (2, ["VPLS", "DMVPN"]), \
                  "ERROR: %s->%s during failure of %s VPLS and %s->%s should be VPLS, DMVPN [%s]" % \
                    (a, b, a, a, b, pth)
              else:
                assert pth == (2, ["DMVPN", "DMVPN"]), \
                  "ERROR: %s->%s during failure of %s VPLS and %s->%s should be 2-hop DMVPN [%s]" % \
                    (a, b, a, a, b, pth)
            else:
              # this pair does not have a DMVPN failure too, so we should
              # be able to one-hop over DMVPN
              assert pth == (1, ["DMVPN"]), \
                "ERROR: %s->%s  during failure of VPLS and %s->%s - should be straight DMVPN [%s]" % \
                  (a, b, a, a, b, pth)
          else:
            if G.node[x]['attr']['vpls'] and G.node[y]['attr']['vpls']:
              assert pth == (1,["VPLS"]), \
                "ERROR: %s->%s during failure of %s VPLS and %s->%s - should remain on VPLS [%s]" % \
                  (x, y, a, a, b, pth)
            elif x in [a,b] and y in [a,b]:
              # both nodes involve in the DMVPN failure
              if not G.node[x]['attr']['vpls'] and G.node[y]['attr']['vpls']:
                assert pth == (2,["DMVPN", "VPLS"]), \
                  "ERROR: %s->%s during failure of %s VPLS and %s->%s should be DMVPN, VPLS [%s]" % \
                    (x, y, a, a, b, pth)
              elif G.nodes[x]['attr']['vpls'] and not G.node[y]['attr']['vpls']:
                assert pth == (2,["VPLS", "DMVPN"]), \
                  "ERROR: %s->%s during failure of %s VPLS and %s->%s should be VPLS, DMVPN [%s]" % \
                    (x, y, a, a, b, pth)
              else:
                assert pth == (2, ["DMVPN", "DMVPN"]), \
                  "ERROR %s->%s during failure of %s VPLS and %s->%s should be DMVPN, DMVPN [%s]" % \
                    (x, y, a, a, b, pth)
            else:
              assert pth == (1,["DMVPN"]), \
                "ERROR: %s->%s during failure of %s VPLS and %s->%s - should remain on DMVPN [%s]" % \
                  (x, y, a, a, b, pth)
    spt_helper.up_links(G, down_links)
  spt_helper.up_links(G, failed_vpls)


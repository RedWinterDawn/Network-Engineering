#!/usr/bin/env python

import jneteng.multigraph as multigraph
from networkx.readwrite import json_graph
import jneteng.http_server as http_server
import json
import getopt
import sys
import jneteng.topology as topology
import jneteng.spt_helper as spt_helper

VPLS_BASE_COST = 100
DMVPN_BASE_COST = 300

DISTANCE_MATRIX_PATH = "data/datacentre-distance-matrix.csv"
NODE_DICTIONARY_PATH = "data/datacentre-info.csv"
LINK_OUTPUT_PATH = "data/link-list.csv"

def usage():
  sys.stderr.write("draw-topology.py -d -v -a <a-end> -z <z-end>\n")

def make_vis(G, a, z, fn):
  paths = multigraph.single_source_dijkstra_rr(G, a, weight='metric')
  if z in paths[1]:
    spt_helper.color_in_paths(G, paths[1][z], penwidth=3)
  d = json_graph.node_link_data(G)
  json.dump(d, open(fn, 'w'))
  spt_helper.reset_graph_colors(G)

def main(argv=None):

  try:
    opts, args = getopt.getopt(argv, 'dva:z:', ["dmvpn-failure", "vpls-failure", "a=", "z="])
  except getopt.GetoptError, m:
    usage()
    sys.exit(1)

  a,z=None,None
  d,v=False,False

  for opt,arg in opts:
    if opt in ('-d', '--dmvpn-failure'):
      d = True
    elif opt in ('-v', '--vpls-failure'):
      v = True
    elif opt in ('-a', '--a'):
      a = arg
    elif opt in ('-z', '--z'):
      z = arg

  if a is None or z is None:
    sys.stderr.write("Must specify a and z ends\n")
    usage()
    sys.exit(1)

  network = topology.build_topology(DISTANCE_MATRIX_PATH, NODE_DICTIONARY_PATH, VPLS_BASE_COST, DMVPN_BASE_COST, LINK_OUTPUT_PATH=LINK_OUTPUT_PATH)
  G = network['graph']
  added = network['link_dict']

  if not a in G or not z in G:
    sys.stderr.write("Invalid nodes specified\n")
    usage()
    sys.exit(1)

  make_vis(G, a, z, 'output/force-before.json')

  down_links = []
  if v:
    down_links = spt_helper.fail_links(G, a, link_class='VPLS')
    make_vis(G, a, z, 'output/force-vpls-failure.json')

  print down_links

  spt_helper.up_links(G, down_links)

  down_links = []
  if d:
    down_links += spt_helper.fail_links(G, a, link_class='DMVPN')
    make_vis(G, a, z, 'output/force-dmvpn-failure.json')

  spt_helper.up_links(G, down_links)

  down_links = spt_helper.fail_links(G, a, specific_link=(a, z, "%s-%s-dmvpn" % (a, z)))
  make_vis(G, a, z, 'output/force-single-dmvpn-failure.json')

  if v:
    down_links = spt_helper.fail_links(G, a, link_class='VPLS')
    make_vis(G, a, z, 'output/force-single-dmvpn-vpls.json')

  http_server.load_url('output/')

if __name__ == '__main__':
  main(sys.argv[1:])

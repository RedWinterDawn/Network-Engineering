import csv
import networkx as nx
import copy
import math
import sys
import re


def build_topology(DISTANCE_MATRIX_PATH, NODE_DICTIONARY_PATH, VPLS_BASE_COST, DMVPN_BASE_COST, LINK_OUTPUT_PATH=False):
  dmvpn_costs = {}
  index = []
  with open(DISTANCE_MATRIX_PATH, 'rb') as csvfile:
    rdr = csv.reader(csvfile, delimiter=',')
    c = 0
    for row in rdr:
      if c == 0:
        for i in range(1,len(row)):
          dmvpn_costs[row[i]] = {}
          index.append(row[i])
      else:
          for i in range(1,len(row)):
            dmvpn_costs[row[0]][index[i-1]] = int(row[i])
      c += 1

  nodes = {}
  names = []
  with open(NODE_DICTIONARY_PATH, 'rb') as csvfile:
    rdr = csv.reader(csvfile,delimiter=',')
    c = 0
    for row in rdr:
      if c == 0:
        for i in row:
          names.append(i)
      else:
        n="asr1k." + row[0].lower().split("-")[0]
        nodes[n] = {}
        for i in range(1,len(row)):
          nodes[n][names[i]] = row[i]
      c += 1

  G = nx.MultiGraph()
  for node in nodes:
    G.add_node(node, attr={"name": node, \
                           "vpls": True if nodes[node]['vpls-connected'] == '1' else False, \
                           "dmvpn": True if nodes[node]['dmvpn-connected'] == '1' else False, \
                           "distance-override": int(nodes[node]['custom-dist']) \
                              if int(nodes[node]['custom-dist']) else False })

  # build DMVPN+VPLS mesh
  added = {}
  for n in nodes:
    added[n] = {}

  if LINK_OUTPUT_PATH:
    link_list = open(LINK_OUTPUT_PATH, 'w')
    link_list.write("""Source", "Destination", "Class", "Metric", "Fixed Metric Component", "Distance Metric Component"\n""")

  for a in G:
    for b in G:
      if not a == b and not a in added[b]:
        w = dmvpn_costs[a.split(".")[1].split("-")[0].upper()][b.split(".")[1].split("-")[0].upper()]

        if not G.node[a]['attr']['distance-override']:
          if not G.node[b]['attr']['distance-override']:
            vpls_base = VPLS_BASE_COST
            dmvpn_base = DMVPN_BASE_COST
          else:
            vpls_base = G.node[b]['attr']['distance-override']+VPLS_BASE_COST
            dmvpn_base = G.node[b]['attr']['distance-override']+DMVPN_BASE_COST
        else:
          vpls_base = G.node[a]['attr']['distance-override']+VPLS_BASE_COST
          dmvpn_base = G.node[a]['attr']['distance-override']+DMVPN_BASE_COST

        if G.node[a]['attr']['vpls'] and G.node[b]['attr']['vpls']:
          G.add_edge(a,b,metric=vpls_base+math.ceil(w/10), cls="VPLS", \
            penwidth=1, count=1, color="lightsteelblue", key="%s-%s-vpls" % (a,b))
          if LINK_OUTPUT_PATH:
            link_list.write("%s,%s,VPLS,%s,%d,%d\n" % (a, b, vpls_base+math.ceil(w/10), vpls_base, math.ceil(w/10)))

        if G.node[a]['attr']['dmvpn'] and G.node[b]['attr']['dmvpn']:
          G.add_edge(a,b,metric=dmvpn_base+math.ceil(w/10), penwidth=1, \
            cls="DMVPN", count=2, color="navajowhite", key="%s-%s-dmvpn" % (a,b))
          if LINK_OUTPUT_PATH:
            link_list.write("%s,%s,DMVPN,%s,%d,%d\n" % (a, b, dmvpn_base+math.ceil(w/10), dmvpn_base, math.ceil(w/10)))

        added[a][b] = "%s-%s" % (a,b)
        added[b][a] = "%s-%s" % (a,b)

  if LINK_OUTPUT_PATH:
    link_list.close()

  return {'graph': G, 'link_dict': added}
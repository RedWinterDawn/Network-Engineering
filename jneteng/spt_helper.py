import copy
import multigraph as multigraph

# Takes a NetworkX graph, and a particular node within it and fails the
# links specified.
#   One of specific_link (a tuple specified as "nodeA", "nodeB", key with
#   key in the format "nodeA-nodeB-class") OR link_class - which
#   corresponds to the 'cls' attribute of the NetworkX links should be
#   specified.
def fail_links(G, node, specific_link=False, link_class=False):
  if not specific_link and not link_class:
    raise AttributeError("must specify either specific_link or link_class")
  #print "asked for %s" % (specific_link)
  removed_links = []
  if link_class:
    neighbors = copy.deepcopy(G[node])
    for neighbor in neighbors:
      link_dict = G[node][neighbor].keys()
      for link in link_dict:
        if G[node][neighbor][link]['cls'] == link_class:
          removed_links.append((node, neighbor, link, copy.deepcopy(G[node][neighbor][link])))
          G.remove_edge(node, neighbor, key=link)
  elif specific_link:
    s = specific_link
    try:
      removed_links.append((s[0], s[1], s[2], G[s[0]][s[1]][s[2]]))
      G.remove_edge(s[0], s[1], key=s[2])
    except KeyError:
      p = s[2].split("-")
      key = p[1] + "-" + p[0] + "-" + p[2]
      removed_links.append((s[0], s[1], key, G[s[0]][s[1]][key]))
      G.remove_edge(s[0], s[1], key=key)
  return removed_links

# Takes the output of fail_links and re-adds them to a NetworkX graph
def up_links(G, links):
  for link in links:
    G.add_edge(link[0], link[1], key=link[2], attr_dict=link[3])

# Set the graph colors back to the default
def reset_graph_colors(G):
  # reset graph colors
  for i in G.nodes():
    for j in G.nodes():
      if i == j:
        continue
      try:
        for k in G[i][j]:
          if 'vpls' in k:
            G[i][j][k]['color'] = 'lightsteelblue'
            G[i][j][k]['penwidth'] = 1
          elif 'dmvpn' in k:
            G[i][j][k]['color'] = 'navajowhite'
            G[i][j][k]['penwidth'] = 1
      except KeyError:
        pass

# Write a PNG of the graph
def write_graph_png(G, filename):
  d = nx.to_pydot(G)
  png_str = d.write_png(filename)

# Colors paths in based on an input of paths that specify segments.
# Each path is a dict with 'route' specified.
def color_in_paths(G, paths, color='#b4d455', penwidth=False, cycle=False):
  colors = ['red', 'green', 'blue', 'orange', 'purple', 'deeppink1', 'deepskyblue3', 'darkgoldenrod2', 'indigo',
          'palevioletred', 'peru']
  index = 0
  for rt in paths['route']:
    for segment in rt:
      if not cycle:
        color = color
      else:
        color = colors[index % len(colors)]
      if isinstance(segment, list):
        for ecmp in segment:
          try:
            G[ecmp[0]][ecmp[1]][ecmp[2]]['color'] = color
            if penwidth:
              G[ecmp[0]][ecmp[1]][ecmp[2]]['penwidth'] = penwidth
          except KeyError:
            raise KeyError("invalid link specified")
      else:
        G[segment[0]][segment[1]][segment[2]]['color'] = color
        if penwidth:
          G[segment[0]][segment[1]][segment[2]]['penwidth'] = penwidth

    index += 1

# Calculates all shortest paths and determines the routes that are
# used within the current tree.
def shortest_path_class(G):
  d_path = multigraph.all_pairs_dijkstra_path_rr(G, weight='metric')
  report_paths = {}
  for a in d_path:
    report_paths[a] = {}
    for b in d_path[a][1]:
      if a == b:
        continue
      report_paths[a][b] = {}
      report_paths[a][b]['ecmp_count'] = len(d_path[a][1][b]['route'])
      report_paths[a][b]['ecmps'] = []
      for ecmp in d_path[a][1][b]['route']:
        ecmp_len = len(ecmp)
        ecmp_components = []
        for sublink in ecmp:
          ecmp_components.append(G[sublink[0]][sublink[1]][sublink[2]]['cls'])
        report_paths[a][b]['ecmps'].append((ecmp_len, ecmp_components))
  return report_paths
#!/usr/bin/env python

import csv
import sys

STAGING_DIR=sys.argv[1]

c = 0
links = []
with open('data/link-list.csv', 'r') as link_file:
  rdr = csv.reader(link_file)
  for row in rdr:
    if c == 0:
      c += 1
      continue
    links.append({'a': row[0],
                  'z': row[1],
                  'cls': row[2],
                  'metric': float(row[3])})

nodes = {}
with open('data/datacentre-info.csv', 'r') as dc_file:
  rdr = csv.reader(dc_file)
  c = 0
  for row in rdr:
    if c == 0:
      c += 1
      continue
    k = row[0].split("-")[0]
    nodes[k] = {
                  'name': row[0],
                  'site-id': row[1],
                  'vpls-connected': row[2],
                  'dmvpn-connected': row[2],
                  'node-loopback': row[3],
                  'tunnel-loopback': row[4],
                }

for link in links:
  a_pop = link['a'].split(".")[1].upper()
  z_pop = link['z'].split(".")[1].upper()

  # on device A then we specify:
  #     neighbor Z cost X
  # for both DMVPNs and both VPLS

  a_fh = open(STAGING_DIR + "/%s-%s-OPSCONTROL" % (a_pop, z_pop), 'a')

  a_fh.write("!\n!\n")
  a_fh.write("! configuration for %s->%s %s link on asr1k.%s\n" % (link['a'], link['z'], link['cls'], a_pop.lower()))
  a_fh.write("router ospf 1 vrf opscontrol\n")
  if link['cls'] == "VPLS":
    a_fh.write(" neighbor 172.16.254.%s cost %d\n" % (nodes[z_pop]['site-id'], link['metric']))
  elif link['cls'] == "DMVPN":
    a_fh.write(" neighbor 172.16.255.%s cost %d\n" % (nodes[z_pop]['site-id'], link['metric']))
  a_fh.write("exit\n!\n")

  a_fh.close()

  a_fh = open(STAGING_DIR + "/%s-%s-INTERNAL" % (a_pop, z_pop), 'a')

  a_fh.write("!\n!\n")
  a_fh.write("! configuration for %s->%s %s link on asr1k.%s\n" % (link['a'], link['z'], link['cls'], a_pop.lower()))
  a_fh.write("router ospf 4 vrf internal\n")
  if link['cls'] == "VPLS":
    a_fh.write(" neighbor 10.255.10.%s cost %d\n" % (nodes[z_pop]['site-id'], link['metric']))
  elif link['cls'] == "DMVPN":
    a_fh.write(" neighbor 10.255.5.%s cost %d\n" % (nodes[z_pop]['site-id'], link['metric']))
  a_fh.write("exit\n!\n")

  a_fh.close()


  z_fh = open(STAGING_DIR + "/%s-%s-OPSCONTROL" % (z_pop, a_pop), 'a')

  z_fh.write("! configuration for %s->%s %s link on asr1k.%s\n" % (link['z'], link['a'], link['cls'], z_pop.lower()))
  z_fh.write("router ospf 1 vrf opscontrol\n")
  if link['cls'] == "VPLS":
    z_fh.write(" neighbor 172.16.254.%s cost %d\n" % (nodes[a_pop]['site-id'], link['metric']))
  elif link['cls'] == 'DMVPN':
    z_fh.write(" neighbor 172.16.255.%s cost %d\n" % (nodes[a_pop]['site-id'], link['metric']))
  z_fh.write("exit\n!\n")

  z_fh.close()

  z_fh = open(STAGING_DIR + "/%s-%s-INTERNAL" % (z_pop, a_pop), 'a')

  z_fh.write("! configuration for %s->%s %s link on asr1k.%s\n" % (link['z'], link['a'], link['cls'], z_pop.lower()))
  z_fh.write("router ospf 4 vrf internal\n")
  if link['cls'] == "VPLS":
    z_fh.write(" neighbor 10.255.10.%s cost %d\n" % (nodes[a_pop]['site-id'], link['metric']))
  elif link['cls'] == 'DMVPN':
    z_fh.write(" neighbor 10.254.10.%s cost %d\n" % (nodes[a_pop]['site-id'], link['metric']))
  z_fh.write("exit\n!\n")

  z_fh.close()
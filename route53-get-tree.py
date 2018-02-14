# This Python file uses the following encoding: utf-8
import sys, re, getopt, traceback
from boto.route53.connection import Route53Connection
import pygraphviz
from colorama import init
from colorama import Fore, Back, Style
init(autoreset=True)

#initialize some stuff
quiet=False
graphfile=False
depth=1
maxdepth=20

def usage():
    print '''Walk a tree of CNAME and A records in a DNS zone on Amazon Route53.

Usage:
  route53-get-tree.py -h -q [ -g <graph filename> ] [ -d <max depth> ] -z <zone name> -n <name1>,...
'''

try:
    opts, args = getopt.getopt(sys.argv[1:], "qhz:n:g:d:")
except getopt.GetoptError as err:
    print str(err)
    usage()
    sys.exit(1)

for o, a in opts:
    if o == "-h":
        usage()
        sys.exit(1)
    elif o == "-z":
        ZONE=a
    elif o == "-n":
        NAMES=a.split(',')
    elif o == "-q":
        quiet=True
    elif o == "-g":
        graphfile=a
    elif o == "-d":
        maxdepth=int(a)
        
c = Route53Connection()
zone=c.get_zone(ZONE)
allrecords=zone.get_records()

if graphfile:
    thegraph=pygraphviz.AGraph(directed=True,rankdir='TB')

def putadot(name):
    if not re.search('\.$',name):
        return name + "."
    else:
        return name

def printrecord(record,my_depth,fgcolor):
    whitespace=""
    for tab in range(1,my_depth):
        whitespace+="\t"
    string="{}{}↳ {} {}".format(whitespace,fgcolor,record.type,', '.join(record.resource_records))
    if record.region:
        string+=" {}[LBR:{}]{}".format(Fore.MAGENTA,record.region,fgcolor)
    elif record.weight:
        if int(record.weight)==0:
            string+=" {}{}[WRR:{}]{}{}".format(Fore.BLACK,Back.RED,record.weight,fgcolor,Back.RESET)
        else:
            string+=" {}[WRR:{}]{}".format(Fore.RED,record.weight,fgcolor)
    if record.identifier:
        string+=" ({})".format(record.identifier)
    if record.type == 'CNAME' and not record.resource_records[0].endswith('.'):
        string+=" {}{}Warning no . at end of CNAME right hand side.{}{}".format(Fore.BLACK,Back.RED,fgcolor,Back.RESET)
    print string

def graphrecord(record,nodecolor):
    global thegraph

    nodeidentifier=""
    edgelabel=""
    edgefontcolor=""
    if record.identifier:
        nodeidentifier+="\n({})".format(record.identifier)
    if record.region:
        edgelabel="{}".format(record.region)
        edgefontcolor="magenta"
    elif record.weight:
        if int(record.weight)==0:
            edgefontcolor="red"
        edgelabel="{}".format(record.weight)

    if record.type == 'CNAME':
        nodename=putadot(record.resource_records[0])
        thegraph.add_node(nodename,label="{} {}{}".format(record.type,nodename,nodeidentifier),color=nodecolor,style='filled')
        thegraph.add_edge(record.name,nodename,label=edgelabel,fontcolor=edgefontcolor)
    elif record.type == 'A':
        nodename=",".join(record.resource_records)
        thegraph.add_node(nodename,label="{} {}{}".format(record.type,nodename,nodeidentifier),color=nodecolor,style='filled')
        thegraph.add_edge(record.name,nodename,label=edgelabel,fontcolor=edgefontcolor)

def recurseCNAMEsorArecords(my_zone,my_allrecords,my_NAME,my_depth):
    global quiet
    global graphfile
    if graphfile:
        global thegraph
    CNAMErecords=list()
    Arecords=list()

    my_NAME=putadot(my_NAME)
    for record in my_allrecords:
        if record.name==my_NAME and record.type=='CNAME':
            CNAMErecords.append(record)
        elif record.name==my_NAME and record.type=='A':
            Arecords.append(record)

    if CNAMErecords and Arecords:
        print "Thats weird, both CNAME and A records came back for the name. The route53 control panel doesn't allow this:"
        print CNAMErecords
        print Arecords
        return False
    elif CNAMErecords:
        for record in CNAMErecords:
            # if we hit max depth, don't recurse anymore
            # if the value of this record is not in our zone, don't recurse anymore
            # the right hand side of the CNAME should end with a . or this will have trouble
            if my_depth<maxdepth and putadot(record.resource_records[0]).endswith(my_zone.name):
                if graphfile:
                    graphrecord(record,'cyan')
                if not quiet:
                    printrecord(record,my_depth,Fore.CYAN)
                try:
                    recurseCNAMEsorArecords(my_zone,my_allrecords,record.resource_records[0],my_depth+1)
                except:
                    print "could not recurse {}".format(record.resource_records)
                    traceback.print_exc()
            else:
                if graphfile:
                    graphrecord(record,'chartreuse')
                if not quiet:
                    printrecord(record,my_depth,Fore.GREEN)
    elif Arecords:
        for record in Arecords:
            if graphfile:
                graphrecord(record,'chartreuse')
            if not quiet:
                printrecord(record,my_depth,Fore.GREEN)
    else:
        return False

for name in NAMES:
    name=putadot(name)
    if not quiet:
        print name # the root name
    if graphfile:
        thegraph.add_node(name)
    recurseCNAMEsorArecords(zone,allrecords,name,depth)

if graphfile:
    thegraph.draw(graphfile,prog='dot')

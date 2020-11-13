# This Python file uses the following encoding: utf-8
import sys, re, getopt, traceback
import boto3
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
    print('''Walk a tree of CNAME and A or AAAA records in a DNS zone on Amazon Route53.

Usage:
  route53-get-tree.py -h -q [ -g <graph filename> ] [ -d <max depth> ] -z <zone name> -n <name1>,...
''')

try:
    opts, args = getopt.getopt(sys.argv[1:], "qhz:n:g:d:")
except getopt.GetoptError as err:
    print(str(err))
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
        
def putadot(name):
    if not re.search('\.$',name):
        return name + "."
    else:
        return name

def printrecord(record,my_depth,fgcolor):
    values = [ rr["Value"] for rr in record["ResourceRecords"] ]
    whitespace=""
    for tab in range(1,my_depth):
        whitespace+="\t"
    string="{}{}↳ {} {}".format(whitespace,fgcolor,record["Type"],', '.join(values))
    if record.get("Region") is not None:
        string+=" {}[LBR:{}]{}".format(Fore.MAGENTA,record["Region"],fgcolor)
    elif record.get("Weight") is not None:
        if int(record["Weight"])==0:
            string+=" {}{}[WRR:{}]{}{}".format(Fore.BLACK,Back.RED,record["Weight"],fgcolor,Back.RESET)
        else:
            string+=" {}[WRR:{}]{}".format(Fore.RED,record["Weight"],fgcolor)
    if record.get("SetIdentifier") is not None:
        string+=" ({})".format(record["SetIdentifier"])
    if record["Type"] == 'CNAME' and not values[0].endswith('.'):
        string+=" {}{}Warning no . at end of CNAME right hand side.{}{}".format(Fore.BLACK,Back.RED,fgcolor,Back.RESET)
    print(string)

def graphrecord(record,nodecolor):
    global thegraph

    values = [ rr["Value"] for rr in record["ResourceRecords"] ]
    nodeidentifier=""
    edgelabel=""
    edgefontcolor=""
    if record.get("Region") is not None:
        edgelabel="{}".format(record["Region"])
        edgefontcolor="magenta"
    elif record.get("Weight") is not None:
        if int(record["Weight"])==0:
            edgefontcolor="red"
        edgelabel="{}".format(record["Weight"])
    if record.get("SetIdentifier") is not None:
        nodeidentifier+="\n({})".format(record["SetIdentifier"])

    if record["Type"] == 'CNAME':
        nodename=putadot(values[0])
        thegraph.add_node(nodename,label="{} {}{}".format(record["Type"],nodename,nodeidentifier),color=nodecolor,style='filled')
        thegraph.add_edge(record["Name"],nodename,label=edgelabel,fontcolor=edgefontcolor)
    elif record["Type"] == 'A' or record["Type"] == 'AAAA':
        nodename=",".join(values)
        thegraph.add_node(nodename,label="{} {}{}".format(record["Type"],nodename,nodeidentifier),color=nodecolor,style='filled')
        thegraph.add_edge(record["Name"],nodename,label=edgelabel,fontcolor=edgefontcolor)

def recurseCNAMEsorAddressRecords(my_zone,my_allrecords,my_NAME,my_depth):
    global quiet
    global graphfile
    if graphfile:
        global thegraph
    CNAMErecords=list()
    Arecords=list()
    AAAArecords=list()

    my_NAME=putadot(my_NAME)
    for record in my_allrecords:
        if record["Name"]==my_NAME and record["Type"]=='CNAME':
            CNAMErecords.append(record)
        elif record["Name"]==my_NAME and record["Type"]=='A':
            Arecords.append(record)
        elif record["Name"]==my_NAME and record["Type"]=='AAAA':
            AAAArecords.append(record)

    if CNAMErecords and (Arecords or AAAArecords):
        print("Thats weird, both CNAME and A or AAAA records came back for the name. The route53 control panel doesn't allow this:")
        print(CNAMErecords)
        print(Arecords)
        return False
    elif CNAMErecords:
        for record in CNAMErecords:
            # if we hit max depth, don't recurse anymore
            # if the value of this record is not in our zone, don't recurse anymore
            # the right hand side of the CNAME should end with a . or this will have trouble
            CNAMEvalue=record["ResourceRecords"][0]["Value"]
            if my_depth<maxdepth and putadot(CNAMEvalue).endswith(my_zone["Name"]):
                if graphfile:
                    graphrecord(record,'cyan')
                if not quiet:
                    printrecord(record,my_depth,Fore.CYAN)
                try:
                    recurseCNAMEsorAddressRecords(my_zone,my_allrecords,CNAMEvalue,my_depth+1)
                except:
                    print("could not recurse {}".format(record["ResourceRecords"]))
                    traceback.print_exc()
            else:
                if graphfile:
                    graphrecord(record,'chartreuse')
                if not quiet:
                    printrecord(record,my_depth,Fore.GREEN)
    elif Arecords or AAAArecords:
        for record in Arecords + AAAArecords:
            if graphfile:
                graphrecord(record,'chartreuse')
            if not quiet:
                printrecord(record,my_depth,Fore.GREEN)
    else:
        return False

ZONE = putadot(ZONE)
client = boto3.client('route53')
zone = [zone for zone in client.list_hosted_zones()["HostedZones"] if zone["Name"] == ZONE][0]

allrecords=list()
paginator = client.get_paginator('list_resource_record_sets')
page_iterator = paginator.paginate(HostedZoneId=zone["Id"])
for page in page_iterator:
    allrecords += page["ResourceRecordSets"]

if graphfile:
    thegraph=pygraphviz.AGraph(directed=True,rankdir='TB')

for name in NAMES:
    name=putadot(name)
    if not quiet:
        print(name) # the root name
    if graphfile:
        thegraph.add_node(name)
    recurseCNAMEsorAddressRecords(zone,allrecords,name,depth)

if graphfile:
    thegraph.draw(graphfile,prog='dot')

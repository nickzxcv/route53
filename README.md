# route53
Some scripts for monitoring Amazon AWS route53

* route53-get-tree.py
...Generates an ASCII or Graphviz diagram of a DNS global load balancing
...structure in route53 that uses CNAME and A records, and Latency and
...Weighted routing policies.

* route53-get-zones2repo.py
...Gets all records from a zone and prints them one by one in XML form
...into a file which is checked into a git repo to monitor changes.

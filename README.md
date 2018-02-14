# route53
Some scripts for monitoring Amazon AWS route53

* route53-get-tree.py

  Generates an ASCII or Graphviz diagram of a DNS global load balancing structure in route53 that uses CNAME and A records, and Latency and Weighted routing policies.
  * https://github.com/nschmalenberger/route53/blob/master/052.m.example.com.svg balances traffic to the nearest location but can optionally send a weighted amount of traffic elsewhere.
  * https://github.com/nschmalenberger/route53/blob/master/download.example.com.svg balances traffic among several CDNs, with a geolocation routing specific to China.

* route53-get-zones2repo.py

  Gets all records from a zone and prints them one by one in XML form into a file which is checked into a git repo to monitor changes.

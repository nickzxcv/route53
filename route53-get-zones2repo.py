#!/usr/bin/env python
import os,shutil
import git
from boto.route53.connection import Route53Connection

initialcommit=False
repo_dir="./zones"

if not os.path.exists(repo_dir):
    repo=git.Repo.init(repo_dir)
    shutil.copyfile("git-commit-notifier.post-commit.hook",os.path.join(repo_dir,".git/hooks/post-commit"))
    os.chmod(os.path.join(repo_dir,".git/hooks/post-commit"),755)
    initialcommit=True
else:
    repo=git.Repo(repo_dir)
os.chdir(repo_dir)

c = Route53Connection()

for zone in c.get_zones():
    zonefilename=zone.name+"xml"
    with open(zonefilename, 'w') as route53zonefile:
        for record in zone.get_records():
            route53zonefile.write(record.to_xml()+"\n\n")
    route53zonefile.closed
    repo.index.add([zonefilename])

if not initialcommit:
    if repo.index.diff('HEAD'):
        commitmessage="added or modified:"
        for diffmember in repo.index.diff('HEAD'):
            commitmessage+=" {}".format(diffmember.b_path)
        repo.index.commit(commitmessage)
else:
    repo.index.commit("initial route53 zone dump")

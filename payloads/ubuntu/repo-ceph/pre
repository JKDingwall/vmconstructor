#!/bin/bash

set -e

# James Dingwall
# Setup the ceph repository

apt-key add - < repo-ceph.key

cat << EOF > /etc/apt/sources.list.d/ceph.list
# http://www.ceph.com/
deb http://ceph.com/debian/ $(lsb_release -sc) main
EOF

apt-get update

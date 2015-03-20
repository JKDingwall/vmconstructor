#!/bin/bash

set -e

# James Dingwall
# Setup the bcache repository

apt-key add - < repo-bcache.key

cat << EOF > /etc/apt/sources.list.d/bcache.list
# http://bcache.evilpiepirate.org/
# https://launchpad.net/~g2p/+archive/ubuntu/storage
deb http://ppa.launchpad.net/g2p/storage/ubuntu $(lsb_release -sc) main
deb-src http://ppa.launchpad.net/g2p/storage/ubuntu $(lsb_release -sc) main
EOF

apt-get update

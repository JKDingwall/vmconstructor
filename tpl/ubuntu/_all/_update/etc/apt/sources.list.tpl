<%def name="install(i)"><%
    i["filename"] = "/etc/apt/sources.list"
%></%def>\
# deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]} main restricted

# deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-updates main restricted
# deb http://security.ubuntu.com/ubuntu ${vmyml["release"]}-security main restricted

# See http://help.ubuntu.com/community/UpgradeNotes for how to upgrade to
# newer versions of the distribution.
deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]} main restricted
deb-src ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]} main restricted

<%text>## Major bug fix updates produced after the final release of the
## distribution.</%text>
deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-updates main restricted
deb-src ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-updates main restricted

<%text>## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu
## team. Also, please note that software in universe WILL NOT receive any
## review or updates from the Ubuntu security team.</%text>
deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]} universe
deb-src ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]} universe
deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-updates universe
deb-src ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-updates universe

<%text>## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu 
## team, and may not be under a free licence. Please satisfy yourself as to 
## your rights to use the software. Also, please note that software in 
## multiverse WILL NOT receive any review or updates from the Ubuntu
## security team.</%text>
deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]} multiverse
deb-src ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]} multiverse
deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-updates multiverse
deb-src ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-updates multiverse

<%text>## N.B. software from this repository may not have been tested as
## extensively as that contained in the main release, although it includes
## newer versions of some applications which may provide useful features.
## Also, please note that software in backports WILL NOT receive any review
## or updates from the Ubuntu security team.</%text>
deb ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-backports main restricted universe multiverse
deb-src ${ymlcfg["ubuntu"]["archive"]} ${vmyml["release"]}-backports main restricted universe multiverse

deb http://security.ubuntu.com/ubuntu ${vmyml["release"]}-security main restricted
deb-src http://security.ubuntu.com/ubuntu ${vmyml["release"]}-security main restricted
deb http://security.ubuntu.com/ubuntu ${vmyml["release"]}-security universe
deb-src http://security.ubuntu.com/ubuntu ${vmyml["release"]}-security universe
deb http://security.ubuntu.com/ubuntu ${vmyml["release"]}-security multiverse
deb-src http://security.ubuntu.com/ubuntu ${vmyml["release"]}-security multiverse

<%text>## Uncomment the following two lines to add software from Canonical's
## 'partner' repository.
## This software is not part of Ubuntu, but is offered by Canonical and the
## respective vendors as a service to Ubuntu users.</%text>
# deb http://archive.canonical.com/ubuntu ${vmyml["release"]} partner
# deb-src http://archive.canonical.com/ubuntu ${vmyml["release"]} partner

<%text>## Uncomment the following two lines to add software from Ubuntu's
## 'extras' repository.
## This software is not part of Ubuntu, but is offered by third-party
## developers who want to ship their latest software.</%text>
# deb http://extras.ubuntu.com/ubuntu ${vmyml["release"]} main
# deb-src http://extras.ubuntu.com/ubuntu ${vmyml["release"]} main

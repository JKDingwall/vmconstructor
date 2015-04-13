<%def name="install(i)"><%
    i["filename"] = "/etc/init/openvswitch-switch.conf"
    i["phase"] = ["POST"]
    i["sha256"] = [
        "e2471490a4e5517e6a7ee80e1d867c4bc2c20b914b00c2f69827342fdf5cd137"
    ]
%></%def><%text>\
# vim: set ft=upstart ts=2 et:
description "Open vSwitch switch"
author "James Page <james.page@ubuntu.com"

start on (local-filesystems and net-device-up IFACE=lo)
stop on runlevel [!2345]

pre-start script
  (test -x /usr/sbin/ovs-vswitchd && test -x /usr/sbin/ovsdb-server) || exit 0

  . /usr/share/openvswitch/scripts/ovs-lib
  test -e /etc/default/openvswitch-switch && . /etc/default/openvswitch-switch

  if ovs_ctl load-kmod; then
    :
  else
    echo "Module has probably not been built for this kernel."
    if ! test -d /usr/share/doc/openvswitch-datapath-dkms; then
      echo "Install the openvswitch-datapath-dkms package."
    fi

    if test X"$OVS_MISSING_KMOD_OK" = Xyes; then
      # We're being invoked by the package postinst.  Do not
      # fail package installation just because the kernel module
      # is not available.
      exit 0
    fi
  fi
  set ovs_ctl start --system-id=random
  if test X"$FORCE_COREFILES" != X; then
    set "$@" --force-corefiles="$FORCE_COREFILES"
  fi
  set "$@" $OVS_CTL_OPTS
  "$@" || exit $?
  ########## PATCH START ##############
  # start the bridges
  bridges=$(ifquery --allow ovs -l)
  [ -n "${bridges}" ] && ifup --allow=ovs ${bridges}
  logger -t ovs-start pre-start end
  ########## PATCH END ################
end script

post-stop script
  ########### PATCH START ################
  logger -t ovs-stop post-stop
  bridges=$(ifquery --allow ovs -l)
  [ -n "${bridges}" ] && ifdown --allow=ovs ${bridges}
  ######### PATCH END ##############
  . /usr/share/openvswitch/scripts/ovs-lib
  test -e /etc/default/openvswitch-switch && . /etc/default/openvswitch-switch

  ovs_ctl stop
end script</%text>

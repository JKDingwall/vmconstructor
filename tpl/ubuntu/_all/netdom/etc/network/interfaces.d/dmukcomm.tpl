<%def name="install(i)"><%
    i["filename"] = "/etc/network/interfaces.d/dmukcomm"
%></%def>\
allow-ovs dmukcomm
iface dmukcomm inet manual
    ovs_type OVSBridge
    ovs_ports dmukbond


allow-dmukcomm dmukbond
iface dmukbond inet manual
    ovs_bridge dmukcomm
    ovs_type OVSBond
    ovs_bonds eth0 eth1 eth2 eth3
    ovs_options other_config:lacp-port-id=103 bond_fake_iface=true bond_mode=balance-slb lacp=active other_config:lacp-time=fast bond_updelay=2000 bond_downdelay=400

iface dmukbond inet6 manual

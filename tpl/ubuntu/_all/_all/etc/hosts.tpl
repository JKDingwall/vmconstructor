<%def name="install(i)"><%
    i["filename"] = "/etc/hosts"
%></%def>\
<%
    print(vmyml)
    try:
        hostname = vmyml["data"].get("hostname", "ubuntu")
    except KeyError:
        hostname = "ubuntu"
%>\
127.0.0.1	localhost
127.0.1.1	${hostname}

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters

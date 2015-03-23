<%def name="install(i)"><%
    i["filename"] = "/etc/default/grub.d/xen.cfg"
#    i["sha256"] = [
#        "2d992650d4f0ee381995119b6b80d31bef20978232b3786fc71e00a2cf53987c"
#    ]
%></%def>\
#
# Uncomment the following variable and set to 0 or 1 to avoid warning.
#
XEN_OVERRIDE_GRUB_DEFAULT=1

echo "Including Xen overrides from /etc/default/grub.d/xen.cfg"

#
# When running update-grub with the Xen hypervisor installed, there are
# some additional variables that can be used to pass options to the
# hypervisor or the dom0 kernel.

# The following two are used to generate arguments for the hypervisor:
#
GRUB_CMDLINE_XEN_DEFAULT="dom0_mem=2048M,max:2048M tmem tmem_dedup=on tmem_compress=on com3=115200,8n1 console=com3,vga"
GRUB_CMDLINE_XEN=""
#
# For example:
#
# dom0_mem=<size>[M]:max=<size>[M]
#   Sets the amount of memory dom0 uses (max prevents balloning for more)
# com[12]=<speed>,<data bits><parity><stopbits>
#   Initialize a serial console from in the hypervisor (eg. 115200,8n1)
#   Note that com1 would be ttyS0 in Linux.
# console=<dev>[,<dev> ...]
#   Redirects Xen hypervisor console (eg. com1,vga)

#
# The next two lines are used for creating kernel arguments for the dom0
# kernel. This allows to have different options for the same kernel used
# natively or as dom0 kernel.
#
GRUB_CMDLINE_LINUX_XEN_REPLACE_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT"
GRUB_CMDLINE_LINUX_XEN_REPLACE="$GRUB_CMDLINE_LINUX tmem console=hvc0 console=tty0 earlyprintk=xenboot"
#
# For example:
#
# earlyprintk=xenboot
#   Allows to send early printk messages to the Xen hypervisor console
# console=hvc0
#   Redirects the Linux console to the hypervisor console

#
# Make booting into Xen the default if not changed above. Finding the
# current string for it always has been a problem.
#
if [ "$XEN_OVERRIDE_GRUB_DEFAULT" = "" ]; then
        echo "WARNING: GRUB_DEFAULT changed to boot into Xen by default!"
        echo "         Edit /etc/default/grub.d/xen.cfg to avoid this warning."
        XEN_OVERRIDE_GRUB_DEFAULT=1
fi
if [ "$XEN_OVERRIDE_GRUB_DEFAULT" = "1" ]; then
        GRUB_DEFAULT="Ubuntu GNU/Linux, with Xen hypervisor"
fi

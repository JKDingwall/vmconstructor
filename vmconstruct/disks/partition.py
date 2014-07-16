import abc
import logging
import uuid
from binascii import crc32
from random import choice
from sparse_list import SparseList


# There really should be no need to change these unless trying to generate something unusual.  Not well
# tested with non default values!
MBR_SECTOR_SIZE = 512		# size for calculation when generating a mbr partition table

GPT_SECTOR_SIZE = 512		# size for calculation when generating a guid partition table
GPT_PTE_SIZE = 128		# size of a gpt partition entry (128 is usual)
GPT_PTE_ENTS = 128		# number of entries in the gpt pte array (128 is usual)

"""
TODO:

correctly generate chs values in mbr for small disks
gpt update first usable / last usable sector in header
map well known mbr types to a table
map will known gpt type uuid to a table
generate a random uuid for gpt header
"""


_partitionTypes = []

class partitionType(object):
    def __init__(self, gptCode, uuidStr, os, code, type):
        self._code = code
        self._uuid = uuid.UUID("{{{uuid}}}".format(uuid=uuidStr))
        self._gptCode = gptCode
        self._mbrCode = (gptCode >> 8) if not ((gptCode | 0xff00) ^ 0xff00) else -1
        self._type = type

        _partitionTypes.append(self)



# Well know guid partition table pte guids (http://en.wikipedia.org/wiki/GUID_Partition_Table)
# http://sourceforge.net/p/gptfdisk/code/ci/master/tree/parttypes.cc#l70
# Comments in the partitionType registrations are copied verbatim from gptfdisk code

# Start with the "unused entry," which should normally appear only
# on empty partition table entries....
partitionType(0x0000, "00000000-0000-0000-0000-000000000000", None,          "null",                "Unused entry")

# DOS/Windows partition types, most of which are hidden from the "L" listing
# (they're available mainly for MBR-to-GPT conversions).
partitionType(0x0100, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/fat-12",      "Microsoft basic data (FAT-12)")
partitionType(0x0400, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/fat-16lt32",  "Microsoft basic data (FAT-16 < 32M)")
partitionType(0x0600, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/fat-16",      "Microsoft basic data (FAT-16)")
partitionType(0x0700, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/ntfs",        "Microsoft basic data (NTFS (or HPFS))")
partitionType(0x0b00, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/fat-32",      "Microsoft basic data (FAT-32)")
partitionType(0x0c00, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/fat-32-lba",  "Microsoft basic data (FAT-32 LBA)")
partitionType(0x0c01, "E3C9E316-0B5C-4DB8-817D-F92DF00215AE", "Windows",     "windows/reserved",    "Microsoft reserved")
partitionType(0x0e00, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/fat-16-lba",  "Microsoft basic data (FAT-16 LBA)")
partitionType(0x1100, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/hfat-12",     "Microsoft basic data (Hidden FAT-12)")
partitionType(0x1400, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/hfat-16lt32", "Microsoft basic data (Hidden FAT-16 < 32M)")
partitionType(0x1600, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/hfat-16",     "Microsoft basic data (Hidden FAT-16)")
partitionType(0x1700, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/hntfs",       "Microsoft basic data (Hidden NTFS (or HPFS))")
partitionType(0x1b00, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/hfat-32",     "Microsoft basic data (Hidden FAT-32)")
partitionType(0x1c00, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/hfat-32-lba", "Microsoft basic data (Hidden FAT-32 LBA)")
partitionType(0x1e00, "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7", "Windows",     "windows/hfat-16-lba", "Microsoft basic data (Hidden FAT-16 LBA)")
partitionType(0x2700, "DE94BBA4-06D1-4D40-A16A-BFD50179D6AC", "Windows",     "windows/re",          "Windows RE")

# Open Network Install Environment (ONIE) specific types.
# See http://www.onie.org/ and
# https://github.com/onie/onie/blob/master/rootconf/x86_64/sysroot-lib-onie/onie-blkdev-common
partitionType(0x3000, "7412F7D5-A156-4B13-81DC-867174929325", "ONIE",        "onie/boot",           "ONIE boot")
partitionType(0x3001, "D4E6E2CD-4469-46F3-B5CB-1BFF57AFC149", "ONIE",        "onie/config",         "ONIE config")

# PowerPC reference platform boot partition
partitionType(0x4100, "9E1A2D38-C612-4316-AA26-8B49521E5A8B", "PowerPC",     "powerpc/boot",        "PowerPC PReP boot")

# Windows LDM ("dynamic disk") types
partitionType(0x4200, "AF9B60A0-1431-4F62-BC68-3311714A69AD", "Windows",     "windows/ldm",         "Windows LDM data")
partitionType(0x4201, "5808C8AA-7E8F-42E0-85D2-E1E90434CFB3", "Windows",     "windows/ldmmeta",     "Windows LDM metadata")

# An oddball IBM filesystem....
partitionType(0x7501, "37AFFC90-EF7D-4E96-91C3-2D7AE055B174", "Windows",     "windows/gpfs",        "IBM GPFS")

# ChromeOS-specific partition types...
# Values taken from vboot_reference/firmware/lib/cgptlib/include/gpt.h in
# ChromeOS source code, retrieved 12/23/2010. They're also at
# http://www.chromium.org/chromium-os/chromiumos-design-docs/disk-format.
# These have no MBR equivalents, AFAIK, so I'm using 0x7Fxx values, since they're close
# to the Linux values.
partitionType(0x7f00, "FE3A2A5D-4F32-41A7-B725-ACCC3285A309", "ChromeOS",    "chromeos/kernel",     "ChromeOS kernel")
partitionType(0x7f01, "3CB8E202-3B7E-47DD-8A3C-7FF2A13CFCEC", "ChromeOS",    "chromeos/root",       "ChromeOS root")
partitionType(0x7f02, "2E0A753D-9E48-43B0-8337-B15192CB1B5E", "ChromeOS",    "chromeos/reserved",   "ChromeOS reserved")

# Linux-specific partition types....
partitionType(0x8200, "0657FD6D-A4AB-43C4-84E5-0933C84B4F4F", "Linux",       "linux/swap",          "Linux swap (or Solaris on MBR)")
partitionType(0x8300, "0FC63DAF-8483-4772-8E79-3D69D8477DE4", "Linux",       "linux/filesystem",    "Linux filesystem")
partitionType(0x8301, "8DA63339-0007-60C0-C436-083AC8230908", "Linux",       "linux/reserved",      "Linux reserved")

# See http://www.freedesktop.org/software/systemd/man/systemd-gpt-auto-generator.html
# and http://www.freedesktop.org/wiki/Specifications/DiscoverablePartitionsSpec/
partitionType(0x8302, "933AC7E1-2EB4-4F13-B844-0E14E2AEF915", "Linux",       "linux//home",         "Linux /home")
partitionType(0x8303, "933AC7E1-2EB4-4F13-B844-0E14E2AEF915", "Linux",       "linux/x86/",          "Linux x86 root (/)")
partitionType(0x8304, "4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709", "Linux",       "linux/amd64/",        "Linux x86-64 root (/)")
partitionType(0x8305, "B921B045-1DF0-41C3-AF44-4C6F280D3FAE", "Linux",       "linux/arm64/",        "Linux ARM64 root (/)")
partitionType(0x8306, "3B8F8425-20E0-4F3B-907F-1A25A76F98E8", "Linux",       "linux//srv",          "Linux /srv")
# these two added from wikipedia, no entry in gptfdisk code
partitionType(0x8307, "7FFEC5C9-2D00-49B7-8941-3EA10A5586B7", "Linux",       "linux/crypt",         "Plain dm-crypt")
partitionType(0x8308, "CA7D7CCB-63ED-4C53-861C-1742536059CC", "Linux",       "linux/luks",          "LUKS partition")

# Used by Intel Rapid Start technology
partitionType(0x8400, "D3BFE2DE-3DAF-11DF-BA40-E3A556D89593", None,          "intel/iffs",          "Intel Rapid Start")

# Another Linux type code....
partitionType(0x8e00, "E6D6D379-F507-44C2-A23C-238F2A3DF928", "Linux",       "linux/lvm",           "Linux LVM")

# FreeBSD partition types....
# Note: Rather than extract FreeBSD disklabel data, convert FreeBSD
# partitions in-place, and let FreeBSD sort out the details....
partitionType(0xa500, "516E7CB4-6ECF-11D6-8FF8-00022D09712B", "FreeBSD",     "freebsd/label",       "FreeBSD disklabel")
partitionType(0xa501, "83BD6B9D-7F41-11DC-BE0B-001560B84F0F", "FreeBSD",     "freebsd/boot",        "FreeBSD boot")
partitionType(0xa502, "516E7CB5-6ECF-11D6-8FF8-00022D09712B", "FreeBSD",     "freebsd/swap",        "FreeBSD swap")
partitionType(0xa503, "516E7CB6-6ECF-11D6-8FF8-00022D09712B", "FreeBSD",     "freebsd/ufs",         "FreeBSD UFS")
partitionType(0xa504, "516E7CBA-6ECF-11D6-8FF8-00022D09712B", "FreeBSD",     "freebsd/zfs",         "FreeBSD ZFS")
partitionType(0xa505, "516E7CB8-6ECF-11D6-8FF8-00022D09712B", "FreeBSD",     "freebsd/raid",        "FreeBSD Vinum/RAID")

# Midnight BSD partition types....
partitionType(0xa580, "85D5E45A-237C-11E1-B4B3-E89A8F7FC3A7", "MidnightBSD", "midnightbsd/data",    "Midnight BSD data")
partitionType(0xa581, "85D5E45E-237C-11E1-B4B3-E89A8F7FC3A7", "MidnightBSD", "midnightbsd/boot",    "Midnight BSD boot")
partitionType(0xa582, "85D5E45B-237C-11E1-B4B3-E89A8F7FC3A7", "MidnightBSD", "midnightbsd/swap",    "Midnight BSD swap")
partitionType(0xa583, "0394Ef8B-237E-11E1-B4B3-E89A8F7FC3A7", "MidnightBSD", "midnightbsd/ufs",     "Midnight BSD UFS")
partitionType(0xa584, "85D5E45D-237C-11E1-B4B3-E89A8F7FC3A7", "MidnightBSD", "midnightbsd/zfs",     "Midnight BSD ZFS")
partitionType(0xa585, "85D5E45C-237C-11E1-B4B3-E89A8F7FC3A7", "MidnightBSD", "midnightbsd/raid",    "Midnight BSD Vinum")

# A MacOS partition type, separated from others by NetBSD partition types...
partitionType(0xa800, "55465300-0000-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/ufs",           "Apple UFS")

# NetBSD partition types. Note that the main entry sets it up as a
# FreeBSD disklabel. I'm not 100% certain this is the correct behavior.
partitionType(0xa900, "516E7CB4-6ECF-11D6-8FF8-00022D09712B", "NetBSD",      "netbsd/label",        "NetBSD disklabel")
partitionType(0xa901, "49F48D32-B10E-11DC-B99B-0019D1879648", "NetBSD",      "netbsd/swap",         "NetBSD swap")
partitionType(0xa902, "49F48D5A-B10E-11DC-B99B-0019D1879648", "NetBSD",      "netbsd/ffs",          "NetBSD FFS")
partitionType(0xa903, "49F48D82-B10E-11DC-B99B-0019D1879648", "NetBSD",      "netbsd/lfs",          "NetBSD LFS")
partitionType(0xa904, "2DB519C4-B10F-11DC-B99B-0019D1879648", "NetBSD",      "netbsd/concat",       "NetBSD concatenated")
partitionType(0xa905, "2DB519EC-B10F-11DC-B99B-0019D1879648", "NetBSD",      "netbsd/encrypt",      "NetBSD encrypted")
partitionType(0xa906, "49F48DAA-B10E-11DC-B99B-0019D1879648", "NetBSD",      "netbsd/raid",         "NetBSD RAID")

# Mac OS partition types (See also 0xa800, above)....
partitionType(0xab00, "426F6F74-0000-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/boot",          "Apple boot")
partitionType(0xaf00, "48465300-0000-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/hfs",           "Apple HFS/HFS+")
partitionType(0xaf01, "52414944-0000-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/raid",          "Apple RAID")
partitionType(0xaf02, "52414944-5F4F-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/raidoffline",   "Apple RAID offline")
partitionType(0xaf03, "4C616265-6C00-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/label",         "Apple label")
partitionType(0xaf04, "5265636F-7665-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/tvrecovery",    "AppleTV recovery")
partitionType(0xaf05, "53746F72-6167-11AA-AA11-00306543ECAC", "Mac OS X",    "apple/core",          "Apple Core Storage")
partitionType(0xbf01, "6A898CC3-1DD2-11B2-99A6-080020736631", "Mac OS X",    "apple/zfs",           "Apple ZFS")

# Solaris partition types (one of which is shared with MacOS)
partitionType(0xbe00, "6A82CB45-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/boot",        "Solaris boot")
partitionType(0xbf00, "6A85CF4D-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/root",        "Solaris root")
partitionType(0xbf01, "6A898CC3-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris//usr",        "Solaris /usr")
partitionType(0xbf02, "6A87C46F-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/swap",        "Solaris swap")
partitionType(0xbf03, "6A8B642B-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/backup",      "Solaris backup")
partitionType(0xbf04, "6A8EF2E9-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris//var",        "Solaris /var")
partitionType(0xbf05, "6A90BA39-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris//home",       "Solaris /home")
partitionType(0xbf06, "6A9283A5-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/alternate",   "Solaris alternate sector")
partitionType(0xbf07, "6A945A3B-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/reserved1",   "Solaris Reserved 1")
partitionType(0xbf08, "6A9630D1-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/reserved2",   "Solaris Reserved 2")
partitionType(0xbf09, "6A980767-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/reserved3",   "Solaris Reserved 3")
partitionType(0xbf0a, "6A96237F-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/reserved4",   "Solaris Reserved 4")
partitionType(0xbf0b, "6A8D2AC7-1DD2-11B2-99A6-080020736631", "Solaris",     "solaris/reserved5",   "Solaris Reserved 5")

# I can find no MBR equivalents for these, but they're on the
# Wikipedia page for GPT, so here we go....
partitionType(0xc001, "75894C1E-3AEB-11D3-B7C1-7B03A0000000", "HP-UX",       "hpux/data",           "HP-UX data")
partitionType(0xc002, "E2A1E728-32E3-11D6-A682-7B03A0000000", "HP-UX",       "hpux/service",        "HP-UX service")

# See http://www.freedesktop.org/wiki/Specifications/BootLoaderSpec
partitionType(0xea00, "BC13C2FF-59E6-4262-A352-B275FD6F7172", None,          "freedesktop/boot",    "Freedesktop $BOOT")

# Type code for Haiku; uses BeOS MBR code as hex code base
partitionType(0xeb00, "42465331-3BA3-10F1-802A-4861696B7521", "Haiku",       "haiku/bfs",           "Haiku BFS")

# Manufacturer-specific ESP-like partitions (in order in which they were added)
partitionType(0xed00, "F4019732-066E-4E12-8273-346C5641494F", None,          "sony/system",         "Sony system partition")
partitionType(0xed01, "BFBFAFE7-A34F-448A-9A5B-6213EB736C22", None,          "lenovo/system",       "Lenovo system partition");

# EFI system and related paritions
partitionType(0xef00, "C12A7328-F81F-11D2-BA4B-00A0C93EC93B", None,          "esp",                 "EFI System")
partitionType(0xef01, "024DEE41-33E7-11D3-9D69-0008C781F39F", None,          "mbr",                 "MBR partition scheme")
partitionType(0xef02, "21686148-6449-6E6F-744E-656564454649", None,          "biosboot",            "BIOS boot partition")


# Ceph type codes; see https://github.com/ceph/ceph/blob/9bcc42a3e6b08521694b5c0228b2c6ed7b3d312e/src/ceph-disk#L76-L81
partitionType(0xf800, "4FBD7E29-9D25-41B8-AFD0-062C0CEFF05D", None,          "ceph/osd",            "Ceph OSD")
partitionType(0xf801, "4FBD7E29-9D25-41B8-AFD0-5EC00CEFF05D", None,          "ceph/osd-crypt",      "Ceph dm-crypt OSD")

# Ceph Object Storage Daemon (encrypted)
partitionType(0xf802, "BFBFAFE7-A34F-448A-9A5B-6213EB736C22", None,          "ceph/journal",        "Ceph journal")
partitionType(0xf803, "45B0969E-9B03-4F30-B4C6-5EC00CEFF106", None,          "ceph/journal-crypt",  "Ceph dm-crypt journal")
partitionType(0xf804, "89C57F98-2FE5-4DC0-89C1-F3AD0CEFF2BE", None,          "ceph/create",         "Ceph disk in creation")
partitionType(0xf805, "89C57F98-2FE5-4DC0-89C1-5EC00CEFF2BE", None,          "ceph/create-crypt",   "Ceph dm-crypt disk in creation")

# VMWare ESX partition types codes
partitionType(0xfb00, "AA31E02A-400F-11DB-9590-000C2911D1B8", "VMWare",      "vmware/vmfs",         "VMWare VMFS")
partitionType(0xfb01, "9198EFFC-31C0-11DB-8F78-000C2911D1B8", "VMWare",      "vmware/reserved",     "VMWare reserved")
partitionType(0xfc00, "9D275380-40AD-11DB-BF97-000C2911D1B8", "VMWare",      "vmware/kcore",        "VMWare kcore crash protection")

# A straggler Linux partition type....
partitionType(0xfd00, "A19D880F-05FC-4D3B-A006-743F0F84911E", "Linux",       "linux/raid",          "Linux RAID")


class InvalidPartitionNumber(Exception):
    """
    Raise if the requested partition index is out of range.
    """
    pass



class PartitionTooLarge(Exception):
    """
    Raise if the requested partition size is beyond the capabilities of the
    partition table type.
    """



class _partition(metaclass=abc.ABCMeta):
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._logger.debug("Building empty partition table")
        self._init()


    @abc.abstractmethod
    def _init(self):
        """
        Initialise an empty partition table strucure.
        """
        pass


    @abc.abstractmethod
    def addPartition(self, index, sizemb, fscode, name=None, flags=[]):
        """
        Add a partition table to the structure.
        """
        pass


    @abc.abstractmethod
    def diskSize(self):
        """
        Based on the current partition table propose a disk size that would contain
        all the partitions.
        """
        pass


    @abc.abstractmethod
    def write(self, file):
        """
        Write the partition table to the file in the appropriate place.
        """
        pass


    def makeDisk(self, file):
        """
        Create a suitably sized sparse file and then write the partition table.
        """
        with open(file, "ab") as fp:
            fp.truncate(self.diskSize())

        self.write(file)



class mbr(_partition):
    # http://en.wikipedia.org/wiki/Master_boot_record

    def _init(self):
        # PTE information
        self._partitions = SparseList(0, (None, None))
        self._epartitions = []
        self._bootable = None

        # Binary representation
        self._pt = bytearray(b"\0"*512)		# The mbr is 512 bytes regardless of sector size
        # disk signature
        self._pt[440] = choice(range(0, 256))
        self._pt[441] = choice(range(0, 256))
        self._pt[442] = choice(range(0, 256))
        self._pt[443] = choice(range(0, 256))
        # boot signature
        self._pt[510] = 0x55
        self._pt[511] = 0xaa


    def addPartition(self, index, sizemb, fscode, name=None, flags=[]):
        """
        Register a partition entry for the partition table
        """
        if index not in range(1, 5):
            raise InvalidPartitionNumber()

        try:
            original_entry = self._partitions[index - 1]
            original_bootable = self._bootable

            self._partitions[index - 1] = (sizemb, fscode)
            if "bootable" in flags:
                self._bootable = index - 1

            self._buildPartitions()
        except PartitionTooLarge:
            self._partitions[index - 1] = original_entry
            self._bootable = original_bootable
            self._buildPartitions()
            raise

        self._logger.debug("Registered partition {i}, size {s}Mb, filesystem {fs}, flags {fl}".format(i=index, s=sizemb, fs=fscode, fl=flags))


    def write(self, file):
        self._logger.debug("Writing mbr partition table to {f}".format(f=file))
        with open(file, "rb+") as fp:
            fp.write(self._pt)


    def diskSize(self):
        """
        Iterate over the partition table and calculate the disk size.
        """
        # The 0-2047s = 1Mb
        size = 1
        for (sizemb, filesystem) in self._partitions:
            size += sizemb if sizemb else 0

        return(size*1048576)


    def _buildPartitions(self):
        """
        Refresh the partition table sizes.  We deal with 512 byte sectors but align for 4k sectors.
        """
        # Where the first partition will start
        next_start = 2048

        self._logger.debug("Building partitions with: {p}".format(p=self._partitions))

        for index in range(0, 4):
            (sizemb, filesystem) = self._partitions[index]

            if filesystem == 0xee and len(self._partitions) == 1:
                # a protective mbr for a gpt
                next_start = 1

            offset = 446 + (index * 16)				# start position of this pte

            if not sizemb:
                self._logger.debug("Zeroing PTE for partition {p}".format(p=(index+1)))
                for zero in range(0, 16):
                    self._pt[offset + zero] = 0
            else:
                if index == self._bootable:
                    self._pt[offset + 0x00] = 0x80			# partition type (0x80 = bootable)
                else:
                    self._pt[offset + 0x00] = 0x00

                self._pt[offset + 0x01] = 254				# chs start address (indicate lba)
                self._pt[offset + 0x02] = 255
                self._pt[offset + 0x03] = 255

                self._pt[offset + 0x04] = filesystem			# fs type

                self._pt[offset + 0x05] = self._pt[offset + 0x01]	# chs end address
                self._pt[offset + 0x06] = self._pt[offset + 0x02]
                self._pt[offset + 0x07] = self._pt[offset + 0x03]

                if next_start > (2**32 - 1):
                    raise PartitionTooLarge("The start sector is greater than 2^32-1")
                self._pt[offset + 0x08] = (next_start & 0xff)
                self._pt[offset + 0x09] = (next_start >> 8) & 0xff
                self._pt[offset + 0x0a] = (next_start >> 16) & 0xff
                self._pt[offset + 0x0b] = (next_start >> 24) & 0xff

                # We'll work in 512 byte sectors but make sure we align to 4k byte
                # (1048576 / 4096) * 8 = number of sectors
                sector_count = (sizemb * 2048)
                if sector_count > (2**32 - 1):
                    raise PartitionTooLarge("The partition size is more than 2^32-1 sectors")

                self._pt[offset + 0x0c] = sector_count & 0xff
                self._pt[offset + 0x0d] = (sector_count >> 8) & 0xff
                self._pt[offset + 0x0e] = (sector_count >> 16) & 0xff
                self._pt[offset + 0x0f] = (sector_count >> 24) & 0xff

                next_start += sector_count



class gpt(_partition):
    # http://en.wikipedia.org/wiki/GUID_Partition_Table

    def _init(self):
        self._partitions = SparseList(0, (None, None, None))
        self._ptes = bytearray(b'\0'*(GPT_PTE_SIZE * GPT_PTE_ENTS))

        # Binary representation
        self._ptpri = bytearray(b"\0"*GPT_SECTOR_SIZE)
        # "EFI PART" signature
        self._ptpri[0x00] = 0x45 ; self._ptpri[0x01] = 0x46 ; self._ptpri[0x02] = 0x49 ; self._ptpri[0x03] = 0x20
        self._ptpri[0x04] = 0x50 ; self._ptpri[0x05] = 0x41 ; self._ptpri[0x06] = 0x52 ; self._ptpri[0x07] = 0x54
        # Revision
        self._ptpri[0x08] = 0x00 ; self._ptpri[0x09] = 0x00 ; self._ptpri[0x0a] = 0x01 ; self._ptpri[0x0b] = 0x00
        # Header size (LE)
        self._ptpri[0x0c:0x0c+4] = self._lebytes(0x5c, 4)
        # LBA of this copy (1) (address of other copy generated later) (LE)
        self._ptpri[0x18:0x18+8] = self._lebytes(1, 8)
        # First usable LBA for partitions (LE)
        self._ptpri[0x28:0x28+8] = self._lebytes(2+self._pteSectors(), 8)
        # Disk GUID
        self._ptpri[0x38:0x38+16] = uuid.uuid4().bytes_le
        # Starting LBA of PTE list (2 for primary copy) (LE)
        self._ptpri[0x48:0x48+8] = self._lebytes(2, 8)
        # Number of PTE entries in array (128) (LE) (not number of defined partitions)
        self._ptpri[0x50:0x50+4] = self._lebytes(GPT_PTE_ENTS, 4)
        # Size of PTE (128) (LE)
        self._ptpri[0x54:0x54+4] = self._lebytes(GPT_PTE_SIZE, 4)

        self._updatePts()


    def _pteSectors(self):
        """
        Calculate the number of sectors required to hold the pte array.
        """
        GPT_PTE_RESERVATION = 16384	# 16384 is the minimum value, GPT_PTE_SIZE * GPT_PTE_ENTS default values
        pte_bytes = max(GPT_PTE_RESERVATION, (GPT_PTE_SIZE * GPT_PTE_ENTS))

        self._logger.debug("The partition table requires {x} {size} byte sectors".format(x=(-(-pte_bytes // GPT_SECTOR_SIZE)), size=GPT_SECTOR_SIZE))

        return(-(-pte_bytes // GPT_SECTOR_SIZE))


    def _lebytes(self, val, len=4):
        """
        Calculate the given value as a little endian ordered byte array of the requested size
        """
        bytes = []
        for byte in range(len):
            bytes.append((val >> (byte * 8)) & 0xff)

        return(bytes)


    def _updatePts(self):
        """
        Recalculate secondary header location in primary then make a copy of the primary gpt header
        and update necessary fields.
        """

        # Update LBA of other header copy in primary header (LE) (the final sector should contain the backup header)
        secondaryLBAAddress = (self.diskSize() // GPT_SECTOR_SIZE) - 1
        self._ptpri[0x20:0x20+8] = self._lebytes(secondaryLBAAddress, 8)

        # Blank CRC bytes ready to recalculate them
        self._ptpri[0x10:0x10+4] = self._lebytes(0, 4)

        # generate pte bytes
        start_sector = 2048 # assuming 512 byte sectors, need to adjust for 4096
        for pte in range(GPT_PTE_ENTS):
            (sizemb, filesystem, name) = self._partitions[pte]
            offset = pte * GPT_PTE_SIZE
            if sizemb:
                # partition type guid
                self._ptes[offset:offset+16] = uuid.UUID('{0FC63DAF-8483-4772-8E79-3D69D8477DE4}').bytes_le
                # unique partition uid
                self._ptes[offset+0x10:offset+0x10+16] = uuid.uuid4().bytes_le
                # start lba address (LE)
                self._ptes[offset+0x20:offset+0x20+8] = self._lebytes(start_sector, 8)
                # end lba address (inclusive) (LE)
                pte_sectors = (sizemb * 1048576) // GPT_SECTOR_SIZE
                self._ptes[offset+0x28:offset+0x28+8] = self._lebytes(start_sector + pte_sectors - 1, 8)
                # attribute flags
                # partition name
                nmenc = name.encode("UTF-16-LE") + b'\0'*72
                self._ptes[offset+0x38:offset+0x38+72] = nmenc[:72]

                # work out next starting point
                start_sector += pte_sectors

        # generate pte crc32 and copy into header
        self._ptpri[0x58:0x58+4] = self._lebytes(crc32(self._ptes), 4)

        # Copy the primary header to the secondary
        self._ptsec = self._ptpri[:]

        # in the copy switch the location address around
        for byte in range(8):
            self._ptsec[0x18+byte], self._ptsec[0x20+byte] = self._ptsec[0x20+byte], self._ptsec[0x18+byte]

        # in the copy set the location of the secondary pte array
        disk_sectors = self.diskSize()  // GPT_SECTOR_SIZE
        pte_sectors = self._pteSectors()
        pte_sec_lba = disk_sectors - (pte_sectors + 1)
        self._ptsec[0x48:0x48+8] = self._lebytes(pte_sec_lba, 8)

        # insert last usable lba address
        self._ptpri[0x30:0x30+8] = self._lebytes(pte_sec_lba-1, 8)
        self._ptsec[0x30:0x30+8] = self._lebytes(pte_sec_lba-1, 8)

        # calculate crcs and sub in
        pri_crc = crc32(self._ptpri[:0x5c])
        sec_crc = crc32(self._ptsec[:0x5c])
        for byte in range(4):
            self._ptpri[0x10+byte] = (pri_crc >> (byte * 8)) & 0xff
            self._ptsec[0x10+byte] = (sec_crc >> (byte * 8)) & 0xff


    def addPartition(self, index, sizemb, fscode, name=None, flags=[]):
        if index > GPT_PTE_ENTS:
            raise InvalidPartitionNumber("Only configured to support {n} partitions".format(n=GPT_PTE_ENTS))

        self._partitions[index-1] = (sizemb, fscode, name)
        self._updatePts()


    def write(self, file):
        # Generate the protective mbr
        protective_mbr = mbr()
        try:
            # If the disk is too large to be represented by an mbr partition then limit
            # it to the maximum representable size.
            # -1 to account for the 2048s start position of first pte
            protective_mbr.addPartition(1, (self.diskSize() // 1048576) - 1, 0xee)
        except PartitionTooLarge:
            # maximum size that can be represented by (2**32 - 1) sectors: ((2**32 - 1) * 512) / 1024
            protective_mbr.addPartition(1, 2147483647, 0xee)
        # Zero the mbr disk signature
        protective_mbr._pt[440:440+4] = [0]*4
        # Tickle the chs h value to 255 for partition 1
        protective_mbr._pt[446 + 0x01] = 255

        # Write the data
        # Write the protective mbr at LBA 0 (start of the disk)
        protective_mbr.write(file)

        with open(file, "rb+") as fp:
            # write the primary header after the protective mbr at LBA 1
            fp.seek(GPT_SECTOR_SIZE)
            fp.write(self._ptpri)
            # write the primary copy of the pte array at LBA 2
            fp.write(self._ptes)
            # write the secondary header at LBA -1
            fp.seek(self.diskSize() - GPT_SECTOR_SIZE)
            fp.write(self._ptsec)
            # write the secondary copy of the pte array at LBA -n
            fp.seek(self.diskSize() - ((self._pteSectors() + 1) * GPT_SECTOR_SIZE))
            fp.write(self._ptes)


    def diskSize(self):
        # The 0-2047s = 1Mb, gpt copy at end of disk = 1Mb
        size = 2
        for (sizemb, filesystem, name) in self._partitions:
            size += sizemb if sizemb else 0

        if size < 16:
            diskBytes = 16 * 1048576
        else:
            diskBytes = size * 1048576

        self._logger.debug("Disk size is {b} bytes ({s} {size} byte sectors)".format(b=diskBytes, s=(diskBytes // GPT_SECTOR_SIZE), size=GPT_SECTOR_SIZE))

        return(diskBytes)

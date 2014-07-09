import abc
import logging
from binascii import crc32
from random import choice
from sparse_list import SparseList


"""
TODO:

fix initial errors with crc for gpt
"""

class InvalidParitionNumber(Exception):
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
        self._bootable = None
        self._bytes = self._init()


    @abc.abstractmethod
    def _init(self):
        """
        Initialise an empty partition table strucure.
        """
        pass


    @abc.abstractmethod
    def addPartition(self, index, sizemb, filesystem, bootable=False):
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



class msdos(_partition):
    # http://en.wikipedia.org/wiki/Master_boot_record

    def _init(self):
        # PTE information
        self._partitions = SparseList(0, (None, None))
        self._epartitions = []

        # Binary representation
        empty = bytearray(b"\0"*512)
        # disk signature
        empty[440] = choice(range(0, 256))
        empty[441] = choice(range(0, 256))
        empty[442] = choice(range(0, 256))
        empty[443] = choice(range(0, 256))
        # boot signature
        empty[510] = 0x55
        empty[511] = 0xaa

        return(empty)


    def addPartition(self, index, sizemb, filesystem, bootable=None):
        """
        Register a partition entry for the partition table
        """
        if index not in range(1, 5):
            raise InvalidParitionNumber()

        try:
            original_entry = self._partitions[index - 1]
            original_bootable = self._bootable

            self._partitions[index - 1] = (sizemb, filesystem)
            if bootable:
                self._bootable = index - 1

            self._buildPartitions()
        except PartitionTooLarge:
            self._partitions[index - 1] = original_entry
            self._bootable = original_bootable
            self._buildPartitions()
            raise

        self._logger.debug("Registered partition {i}, size {s}Mb, filesystem {f}, bootable {b}".format(i=index, s=sizemb, f=filesystem, b=bootable))


    def write(self, file):
        self._logger.debug("Writing msdos partition table to {f}".format(f=file))
        with open(file, "rb+") as fp:
            fp.write(self._bytes)


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
                    self._bytes[offset + zero] = 0
            else:
                if index == self._bootable:
                    self._bytes[offset + 0x00] = 0x80		# partition type (0x80 = bootable)
                else:
                    self._bytes[offset + 0x00] = 0x00

                self._bytes[offset + 0x01] = 254		# chs start address (indicate lba)
                self._bytes[offset + 0x02] = 255
                self._bytes[offset + 0x03] = 255

                self._bytes[offset + 0x04] = filesystem		# fs type

                self._bytes[offset + 0x05] = self._bytes[offset + 0x01]	# chs end address
                self._bytes[offset + 0x06] = self._bytes[offset + 0x02]
                self._bytes[offset + 0x07] = self._bytes[offset + 0x03]

                if next_start > (2**32 - 1):
                    raise PartitionTooLarge("The start sector is greater than 2^32-1")
                self._bytes[offset + 0x08] = (next_start & 0xff)
                self._bytes[offset + 0x09] = (next_start >> 8) & 0xff
                self._bytes[offset + 0x0a] = (next_start >> 16) & 0xff
                self._bytes[offset + 0x0b] = (next_start >> 24) & 0xff

                # We'll work in 512 byte sectors but make sure we align to 4k byte
                # (1048576 / 4096) * 8 = number of sectors
                sector_count = (sizemb * 2048)
                if sector_count > (2**32 - 1):
                    raise PartitionTooLarge("The partition size is more than 2^32-1 sectors")

                self._bytes[offset + 0x0c] = sector_count & 0xff
                self._bytes[offset + 0x0d] = (sector_count >> 8) & 0xff
                self._bytes[offset + 0x0e] = (sector_count >> 16) & 0xff
                self._bytes[offset + 0x0f] = (sector_count >> 24) & 0xff

                next_start += sector_count



class gpt(_partition):
    # http://en.wikipedia.org/wiki/GUID_Partition_Table

    def _init(self):
        self._partitions = SparseList(0, (None, None))
        self._ptes = bytearray(b'\0'*(128*128))

        # Binary representation
        empty = bytearray(b"\0"*512)
        # "EFI PART" signature
        empty[0x00] = 0x45 ; empty[0x01] = 0x46 ; empty[0x02] = 0x49 ; empty[0x03] = 0x20
        empty[0x04] = 0x50 ; empty[0x05] = 0x41 ; empty[0x06] = 0x52 ; empty[0x07] = 0x54
        # Revision
        empty[0x08] = 0x00 ; empty[0x09] = 0x00 ; empty[0x0a] = 0x01 ; empty[0x0b] = 0x00
        # Header size (LE)
        empty[0x0c] = 0x5c ; empty[0x0d] = 0x00 ; empty[0x0e] = 0x00 ; empty[0x0f] = 0x00
        # LBA of this copy (1) (address of other copy generated later) (LE)
        empty[0x18] = 0x01 ; empty[0x19] = 0x00 ; empty[0x1a] = 0x00 ; empty[0x1b] = 0x00
        empty[0x1c] = 0x00 ; empty[0x1d] = 0x00 ; empty[0x1e] = 0x00 ; empty[0x1f] = 0x00
        # First usable LBA (2048) (LE)
        empty[0x28] = 0x00 ; empty[0x29] = 0x08 ; empty[0x2a] = 0x00 ; empty[0x2b] = 0x00
        empty[0x2c] = 0x00 ; empty[0x2d] = 0x00 ; empty[0x2e] = 0x00 ; empty[0x2f] = 0x00
        # Disk GUID
        empty[0x38] = 0xde ; empty[0x39] = 0xad ; empty[0x3a] = 0xbe ; empty[0x3b] = 0xef
        empty[0x3c] = 0xde ; empty[0x3d] = 0xad ; empty[0x3e] = 0xbe ; empty[0x3f] = 0xef
        empty[0x40] = 0xde ; empty[0x41] = 0xad ; empty[0x42] = 0xbe ; empty[0x43] = 0xef
        empty[0x44] = 0xde ; empty[0x45] = 0xad ; empty[0x46] = 0xbe ; empty[0x47] = 0xef
        # Starting LBA of PTE list (2 for primary copy) (LE)
        empty[0x48] = 0x02 ; empty[0x49] = 0x00 ; empty[0x4a] = 0x00 ; empty[0x4b] = 0x00
        # Size of PTE (128) (LE)
        empty[0x54] = 0x80 ; empty[0x55] = 0x00 ; empty[0x56] = 0x00 ; empty[0x57] = 0x00

        initial_crc = crc32(empty[:0x5c])
        empty[0x10] = initial_crc & 0xff
        empty[0x11] = (initial_crc >> 8) & 0xff
        empty[0x12] = (initial_crc >> 16) & 0xff
        empty[0x13] = (initial_crc >> 24) & 0xff

        return(empty)


    def addPartition(self, index, sizemb, filesystem, bootable=False):
        raise Exception("not implemented")


    def write(self, file):
        # Generate the protective mbr
        protective_mbr = msdos()
        try:
            # If the disk is too large to be represented by an mbr partition then limit
            # it to the maximum representable size.
            # -1 to account for the 2048s start position of first pte
            protective_mbr.addPartition(1, (self.diskSize() // 1048576) - 1, 0xee)
        except PartitionTooLarge:
            # maximum size that can be represented by (2**32 - 1) sectors: ((2**32 - 1) * 512) / 1024
            protective_mbr.addPartition(1, 2147483647, 0xee)
        # Tickle the chs h value to 255 for parition 1
        protective_mbr._bytes[446 + 0x01] = 255

        # Write the data
        protective_mbr.write(file)

        with open(file, "rb+") as fp:
            fp.seek(len(protective_mbr._bytes))
            fp.write(self._bytes)


    def diskSize(self):
        return(16*1048576)
        raise Exception("not implemented")

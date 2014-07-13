import abc
import logging
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
        self._init()


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
        self._pt = bytearray(b"\0"*512)
        # disk signature
        self._pt[440] = choice(range(0, 256))
        self._pt[441] = choice(range(0, 256))
        self._pt[442] = choice(range(0, 256))
        self._pt[443] = choice(range(0, 256))
        # boot signature
        self._pt[510] = 0x55
        self._pt[511] = 0xaa


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
        self._partitions = SparseList(0, (None, None))
        self._ptes = bytearray(b'\0'*(128*128))

        # Binary representation
        self._ptpri = bytearray(b"\0"*MBR_SECTOR_SIZE)
        # "EFI PART" signature
        self._ptpri[0x00] = 0x45 ; self._ptpri[0x01] = 0x46 ; self._ptpri[0x02] = 0x49 ; self._ptpri[0x03] = 0x20
        self._ptpri[0x04] = 0x50 ; self._ptpri[0x05] = 0x41 ; self._ptpri[0x06] = 0x52 ; self._ptpri[0x07] = 0x54
        # Revision
        self._ptpri[0x08] = 0x00 ; self._ptpri[0x09] = 0x00 ; self._ptpri[0x0a] = 0x01 ; self._ptpri[0x0b] = 0x00
        # Header size (LE)
        self._ptpri[0x0c] = 0x5c ; self._ptpri[0x0d] = 0x00 ; self._ptpri[0x0e] = 0x00 ; self._ptpri[0x0f] = 0x00
        # LBA of this copy (1) (address of other copy generated later) (LE)
        self._ptpri[0x18] = 0x01 ; self._ptpri[0x19] = 0x00 ; self._ptpri[0x1a] = 0x00 ; self._ptpri[0x1b] = 0x00
        self._ptpri[0x1c] = 0x00 ; self._ptpri[0x1d] = 0x00 ; self._ptpri[0x1e] = 0x00 ; self._ptpri[0x1f] = 0x00
        # First usable LBA (2048) (LE)
        self._ptpri[0x28] = 0x00 ; self._ptpri[0x29] = 0x08 ; self._ptpri[0x2a] = 0x00 ; self._ptpri[0x2b] = 0x00
        self._ptpri[0x2c] = 0x00 ; self._ptpri[0x2d] = 0x00 ; self._ptpri[0x2e] = 0x00 ; self._ptpri[0x2f] = 0x00
        # Disk GUID
        self._ptpri[0x38] = 0xde ; self._ptpri[0x39] = 0xad ; self._ptpri[0x3a] = 0xbe ; self._ptpri[0x3b] = 0xef
        self._ptpri[0x3c] = 0xde ; self._ptpri[0x3d] = 0xad ; self._ptpri[0x3e] = 0xbe ; self._ptpri[0x3f] = 0xef
        self._ptpri[0x40] = 0xde ; self._ptpri[0x41] = 0xad ; self._ptpri[0x42] = 0xbe ; self._ptpri[0x43] = 0xef
        self._ptpri[0x44] = 0xde ; self._ptpri[0x45] = 0xad ; self._ptpri[0x46] = 0xbe ; self._ptpri[0x47] = 0xef
        # Starting LBA of PTE list (2 for primary copy) (LE)
        self._ptpri[0x48] = 0x02 ; self._ptpri[0x49] = 0x00 ; self._ptpri[0x4a] = 0x00 ; self._ptpri[0x4b] = 0x00
        # Number of PTE entries in array (128) (LE) (not number of defined partitions)
        self._ptpri[0x50] = 0x80 ; self._ptpri[0x55] = 0x00 ; self._ptpri[0x56] = 0x00 ; self._ptpri[0x57] = 0x00
        # Size of PTE (128) (LE)
        self._ptpri[0x54] = 0x80 ; self._ptpri[0x55] = 0x00 ; self._ptpri[0x56] = 0x00 ; self._ptpri[0x57] = 0x00

        self._updatePts()


    def _pteSectors(self):
        """
        Calculate the number of sectors required to hold the pte array.
        """
        GPT_PTE_RESERVATION = 16384	# 16384 is the minimum value, GPT_PTE_SIZE * GPT_PTE_ENTS default values
        pte_bytes = max(GPT_PTE_RESERVATION, (GPT_PTE_SIZE * GPT_PTE_ENTS))

        self._logger.debug("The partition table requires {x} {size} byte sectors".format(x=(-(-pte_bytes // GPT_SECTOR_SIZE)), size=GPT_SECTOR_SIZE))

        return(-(-pte_bytes // GPT_SECTOR_SIZE))


    def _updatePts(self):
        """
        Recalculate secondary header location in primary then make a copy of the primary gpt header
        and update necessary fields.
        """

        # Update LBA of other copy in primary header (LE) (the final sector should contain the backup header)
        secondaryLBAAddress = (self.diskSize() // MBR_SECTOR_SIZE) - 1
        for byte in range(8):
            self._ptpri[0x20+byte] = (secondaryLBAAddress >> (byte * 8)) & 0xff

        # Blank CRC bytes ready to recalculate them
        for byte in range(4):
            self._ptpri[0x10+byte] = 0

        # generate pte bytes
        for pte in range(128):
            pass

        # generate pte crc32 and copy into header
        pte_crt = crc32(self._ptes)
        for byte in range(4):
            self._ptpri[0x58+byte] = (pte_crt >> (byte * 8)) & 0xff

        # Copy the primary header to the secondary
        self._ptsec = self._ptpri[:]

        # in the copy switch the location address around
        for byte in range(8):
            self._ptsec[0x18+byte], self._ptsec[0x20+byte] = self._ptsec[0x20+byte], self._ptsec[0x18+byte]

        # in the copy set the location of the secondary pte array
        disk_sectors = self.diskSize()  // GPT_SECTOR_SIZE
        pte_sectors = self._pteSectors()
        pte_sec_lba = disk_sectors - (pte_sectors + 1)
        for byte in range(8):
            self._ptsec[0x48+byte] = (pte_sec_lba >> (byte * 8)) & 0xff

        # calculate crcs and sub in
        pri_crc = crc32(self._ptpri[:0x5c])
        sec_crc = crc32(self._ptsec[:0x5c])
        print(hex(pri_crc))
        print(hex(sec_crc))
        for byte in range(4):
            self._ptpri[0x10+byte] = (pri_crc >> (byte * 8)) & 0xff
            self._ptsec[0x10+byte] = (sec_crc >> (byte * 8)) & 0xff


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
        # Zero the mbr disk signature
        protective_mbr._pt[440:440+4] = [0]*4
        # Tickle the chs h value to 255 for parition 1
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
        for (sizemb, filesystem) in self._partitions:
            size += sizemb if sizemb else 0

        if size < 16:
            diskBytes = 16 * 1048576
        else:
            diskBytes = size * 1048576

        self._logger.debug("Disk size is {b} bytes ({s} {size} byte sectors)".format(b=diskBytes, s=(diskBytes // GPT_SECTOR_SIZE), size=GPT_SECTOR_SIZE))

        return(diskBytes)

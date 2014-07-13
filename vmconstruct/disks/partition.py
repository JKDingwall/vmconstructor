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
        self._pt = bytearray(b"\0"*512)		# The mbr is 512 bytes regardless of sector size
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
        self._ptpri[0x38:0x38+16] = uuid.UUID('deadbeefdeadbeefdeadbeefdeadbeef').bytes_le
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


    def addPartition(self, index, sizemb, filesystem, name, bootable=False):
        self._partitions[index-1] = (sizemb, filesystem, name)
        self._updatePts()


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
        for (sizemb, filesystem, name) in self._partitions:
            size += sizemb if sizemb else 0

        if size < 16:
            diskBytes = 16 * 1048576
        else:
            diskBytes = size * 1048576

        self._logger.debug("Disk size is {b} bytes ({s} {size} byte sectors)".format(b=diskBytes, s=(diskBytes // GPT_SECTOR_SIZE), size=GPT_SECTOR_SIZE))

        return(diskBytes)

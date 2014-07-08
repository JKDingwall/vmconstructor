import abc
import logging
from random import choice


class InvalidParitionNumber(Exception):
    """
    Raise if the requested partition index is out of range.
    """
    pass



class _partition(metaclass=abc.ABCMeta):
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._bytes = self._init()


    @abc.abstractmethod
    def _init(self):
        """
        Initialise an empty partition table strucure.
        """
        pass


    @abc.abstractmethod
    def addPartition(self, index, sizemb, filesystem):
        """
        Add a partition table to the structure.
        """


    def write(self, file):
        """
        Write the partition table to the file in the appropriate place.
        """
        self._logger.debug("Writing partition table to {f}".format(f=file))
        with open(file, "rb+") as fp:
            fp.write(self._bytes)



class msdos(_partition):
    # http://en.wikipedia.org/wiki/Master_boot_record
    def _init(self):
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


    def addPartition(self, index, sizemb, filesystem):
        if index not in range(1, 5):
            raise InvalidParitionNumber()

        offset = (446 - 16) + (index * 16) # -16 since we count the partitions 1 - 4
        self._bytes[offset + 0x00] = 0x80			# partition type
        self._bytes[offset + 0x01] = 254			# chs start address
        self._bytes[offset + 0x02] = 255
        self._bytes[offset + 0x03] = 255
        self._bytes[offset + 0x04] = filesystem			# fs type
        self._bytes[offset + 0x05] = self._bytes[offset + 0x01]	# chs end address
        self._bytes[offset + 0x06] = self._bytes[offset + 0x02]
        self._bytes[offset + 0x07] = self._bytes[offset + 0x03]

        if index == 1:
            lba_start = 2048

        self._bytes[offset + 0x08] = (lba_start & 0xff)
        self._bytes[offset + 0x09] = (lba_start >> 8) & 0xff
        self._bytes[offset + 0x0a] = (lba_start >> 16) & 0xff
        self._bytes[offset + 0x0b] = (lba_start >> 24) & 0xff

        # We'll work in 512 byte sectors but make sure we align to 4k byte
        # (1048576 / 4096) * 8 = number of sectors
        sector_count = (sizemb * 2048)

        self._bytes[offset + 0x0c] = sector_count & 0xff
        self._bytes[offset + 0x0d] = (sector_count >> 8) & 0xff
        self._bytes[offset + 0x0e] = (sector_count >> 16) & 0xff
        self._bytes[offset + 0x0f] = (sector_count >> 24) & 0xff

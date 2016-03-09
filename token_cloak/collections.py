import base64
import binascii
from bitarray import bitarray
import hashlib
import os

from .exceptions import ConfigError
from .utils import (
        base64_to_bitarray, bitarray_to_base64, bitarray_to_bytes,
        bitarray_to_hex, bitarray_to_int, bitarray_to_str, bytes_to_bitarray,
        hex_to_bitarray, int_to_bitarray, str_to_bitarray)


class BitCollection:
    """Holds, manipulates, and expresses bitarrays in various formats.
    
    A BitCollection is an abstraction from bitarray, which only supports
    a few interfaces for data. This abstraction focuses on a variety of
    input and output formats, as well as the ability to sew in bits from
    each of these formats.
    """
    
    def __init__(self, b=None):
        """Make a new collection out of a bytearray.
        
        Args:
            b (bitarray): Source to create collection from.
        
        """
        # Setup the parameters
        if b:
            if not isinstance(b, bitarray):
                raise ConfigError('b must be a bitearray')
            self.content = b
        else:
            self.content = bitarray()
    
    
    @classmethod
    def from_base64(cls, s, url_safe=False):
        """Creates a new collection from a base64 string.
        
        Args:
            s (str): A base64 string to ingest to the collection.
            url_safe (Optional[bool]): If true, substitute '-_' with
                '+/'.
        
        Return:
            BitCollection: new instance.
            
        """
        return cls(base64_to_bitarray(s, url_safe=url_safe))
    
    
    @classmethod
    def from_bytes(cls, b):
        """Creates a new collection from a hexidecimal string.
        
        Args:
            b (bytes): Bytes to start a collection with.
        
        Returns:
            BitCollection: new instance.
        
        """
        return cls(bytes_to_bitarray(b))
    
    
    @classmethod
    def from_hex(cls, s):
        """Creates a new collection from a hexidecimal string.
        
        Args:
            s (str): A hexidecimal string to ingest to the
                collection.
        
        Returns:
            BitCollection: new instance.
        
        Raises:
            ValueError: s isn't a valid hexidecimal number.
        
        """
        return cls(hex_to_bitarray(s))
    
    
    @classmethod
    def from_int(cls, i, bits):
        """Creates a new collection from a base64 string.
        
        Args:
            i (int): An integer to encode into bits.
            bits (int): Number of bits to assign this integer to.
        
        Returns:
            BitCollection: new instance.
            
        """
        return cls(int_to_bitarray(i, bits=bits))
    
    
    @classmethod
    def from_random(cls, bits):
        """Generates a totally random BitCollection.
        
        Args:
            bits (int): Length of the BitCollection.
        
        Return:
            BitCollection: new instance.
        
        """
        # The source length needs to be divisible by 8 and encompassing.
        mod = bits % 8
        if mod:
            bits += (8 - mod)
        
        # Generate off the os's better randomness.
        bytes_ = os.urandom(bits // 8)
        
        # Create BitCollection from resulting bytes.
        b = cls.from_bytes(bytes_)
        
        # Shave off undwanted bits.
        if mod:
            for i in range(8 - mod):
                b.pop()
        
        # Return the BitCollection
        return b
    
    
    def extract(self, positions):
        """Extract BitCollection from this collection.
        
        Args:
            positions (list): The positions to extract bits from the
                collection.
        
        Returns:
            BitCollection: bits in the order of extraction.
        
        """
        return self.__class__(self.extract_bitarray(positions=positions))
    
    
    def extract_bitarray(self, positions):
        """Extract bits from this collection at the given positions.
        
        Args:
            positions (list): The positions to extract bits from the
                collection.
        
        Returns:
            bitarray: bits in the order of extraction.
        
        """
        # Roll through each position.
        bits = bitarray()
        for j, position in enumerate(positions):
            
            # Put the value into this collection
            bits.append(self.content.pop(position))
        
        # Return reorder the bits and return
        bits.reverse()
        return bits
    
    
    def extract_bytes(self, positions):
        """Extract bytes from this collection at the given positions.
        
        Args:
            positions (list): The positions to extract bits from the
                collection.
        
        Returns:
            bytes: in the order of extraction.
        
        """
        # Extract the bits
        bits = self.extract_bitarray(positions=positions)
        
        # Convert to bytes
        return bitarray_to_bytes(bits)
    
    
    def extract_int(self, positions):
        """Extract the bits of the integer from this collection.
        
        Args:
            positions (list): The positions to extract bits from the
                collection.
        
        Returns:
            int: in the order of extraction.
        
        """
        # Roll through each position.
        output = 0
        total = len(positions) - 1
        for j, position in enumerate(positions):
            
            # Get the bit from this collection
            bit = self.content.pop(position)
            
            # Add to the output
            output |= bit << (total - j)
        
        # Return the reconstructed integer
        return output
    
    
    def extract_hex(self, positions):
        """Extract a hexadecimal string from this collection.
        
        Args:
            positions (list): The positions to extract bits from the
                collection.
        
        Returns:
            str: hexadecimal string in order of extraction.
        
        """
        # Extract the bits
        bits = self.extract_bitarray(positions=positions)
        
        # Convert to hex
        return bitarray_to_hex(bits)
    
    
    def extract_base64(self, positions, url_safe=False):
        """Extract bits from this collection at the given positions.
        
        Args:
            positions (list): The positions to extract bits from the
                collection.
            url_safe (Optional[bool]): Whether the output string
                contains '-_' instead of '+/'.
        
        Returns:
            str: base64 encoded.
        
        """
        # Extract the bits
        bits = self.extract_bitarray(positions=positions)
        
        # Convert to base64
        return bitarray_to_base64(bits, url_safe=url_safe)
    
    
    def insert(self, b, positions):
        """Insert another BitCollection into this collection.
        
        Args:
            b (BitCollection): Content to insert.
            positions (list): The positions to insert bits into the
                collection.
        
        """
        self.insert_bitarray(b.content, positions=positions)
    
    
    def insert_bitarray(self, b, positions):
        """Insert bits into this collection at the given positions.
        
        Args:
            b (bitarray): Content to insert.
            positions (list): The positions to insert bits into the
                collection.
        
        """
        # Roll through each position.
        for j, position in enumerate(positions):
            
            # Put the value into this collection
            self.content.insert(position, b[j])
    
    
    def insert_bytes(self, b, positions):
        """Insert byte bits into this collection at the given positions.
        
        Args:
            b (bytes|bytearray): Content to insert.
            positions (list): The positions to insert bits into the
                collection.
        
        """
        # Use the bitarray
        bits = bitarray()
        bits.frombytes(b)
        
        # Run the bitarray function
        self.insert_bitarray(bits, positions=positions)
    
    
    def insert_int(self, i, positions):
        """Insert the bits of the integer into this collection.
        
        Args:
            i (int): Content to insert.
            positions (list): The positions to insert bits into the
                collection.
        
        """
        # Roll through each position.
        for j, position in enumerate(positions):
            
            # Get the bit from the integer
            bit = (i & (1 << j)) >> j
            
            # Insert it into the content
            self.content.insert(position, bit)
    
    
    def insert_hex(self, s, positions):
        """Insert a hexadecimal string into this collection.
        
        Args:
            s (str): Hexadecimal string to insert.
            positions (list): The positions to insert bits into the
                collection.
        
        """
        self.insert_bitarray(hex_to_bitarray(s), positions=positions)
    
    
    def insert_base64(self, s, positions, url_safe=False):
        """Insert byte bits into this collection at the given positions.
        
        Args:
            s (str): Base64 string to insert.
            positions (list): The positions to insert bits into the
                collection.
            url_safe (Optional[bool]): Whether the input string contains
                '-_' instead of '+/'.
        
        """
        bits = base64_to_bitarray(s, url_safe=url_safe)
        self.insert_bitarray(bits, positions=positions)
    
    
    def length(self):
        """Return the number of bits stored in the object."""
        if not self.content:
            return 0
        return self.content.length()
    
    
    def pop(self, index=None):
        """Pop the last value off the bitarray."""
        if not index:
            index = self.length() - 1
        return self.content.pop(index)
    
    
    def to_base64(self, url_safe=False):
        """Express this collection as a base64 string.
        
        Args:
            url_safe (Optional[bool]): Whether the output should contain
                '-_' instead of '+/'.
        
        Returns:
            str: base64 encoded.
        
        """
        return bitarray_to_base64(self.content, url_safe=url_safe)
    
    
    def to_bytes(self):
        """Express this collection as bytes."""
        return self.content.tobytes()
    
    
    def to_hex(self):
        """Express this collection as a hexadecimal string."""
        return bitarray_to_hex(self.content)
    
    
    def to_int(self):
        """Express this collection as an integer."""
        return bitarray_to_int(self.content)


class SecretKeyCollection:
    """Standard object to ingest and express a secret key.
    
    Secret keys are provided as strings that will be decoded as ASCII
    characters. Values will be restricted to characters 0x20 thru 0x7F
    and reorganized as compatible bytes in order to maximize entropy.
    """
    
    def __init__(self, s):
        """Initilize a collection with a single secret key."""
        
        # Convert string into bytes according to the ASCII standard.
        bytes_ = bytes(s, 'ascii')
        
        # Loop through bytes and squash into smaller amount of bits.
        bits = bitarray()
        for b in bytes_:
            t = (int(b) - 32) & 0x5F
            bits = int_to_bitarray(t,6) + bits
        
        # Pad if necessary.
        mod = bits.length() % 8
        if mod:
            bits = bitarray('0' * (8 - mod)) + bits
        
        # Keep the data.
        self.original = s
        self.content = BitCollection(bits)
        self.index = 0
    
    
    def chunk(self, n):
        """Spit out even-sized chunks from the secret key bits.
        
        Args:
            n (int): Number of evenly-sized chunks.
            
        Returns:
            list: ints wrapped at 32 bits.
        
        """
        # How big are chunks (in bytes)?
        total_bytes = self.content.length() // 8
        chunk_size = total_bytes // n
        
        # Make sure all characters are used (if size was floored)
        if total_bytes % n:
            chunk_size += 1
        
        # Get the iterator going
        iterator = iter(self.content.to_bytes())
        for a in range(n):
            
            # Build this specific chunk, one char at a time
            bytes_ = bytearray()
            for b in range(chunk_size):
                
                # Add the character to the chunk
                try:
                    bytes_.append(next(iterator))
                
                # String stopped early
                except StopIteration:
                    break
            
            # Hash the bytes.
            m = hashlib.sha256()
            m.update(bytes_)
            d = m.digest()
            
            # Chunk completed, yield the 32 bits as an int.
            yield int.from_bytes(d[0:4], byteorder='big')
            

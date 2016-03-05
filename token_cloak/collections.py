import base64
import binascii
from bitarray import bitarray

from .exceptions import ConfigError
from .utils import int_to_binstr


class BitCollection:
    """Object to hold and manipulate byte arrays.
    
    These collections will be the interface between token data and
    bits that need to be injected and extracted from the data.
    """
    
    def __init__(self, content=None):
        """Make a new collection out of a bytearray.
        
        Args:
            content (bytearray): Source to create collection from.
            bit_length (Optional[int]): Set the initial bit length.
        """
        # Setup the parameters
        bits = bitarray()
        bytes_ = bytearray([])
        if content:
            if not isinstance(content, bytearray):
                raise ConfigError('content must be a bytearray')
            bytes_ = content
            
            # Populate it with the bytearray info.
            for byte_ in bytes_:
                bits += bitarray(int_to_binstr(byte_, bits=8))
        
        # Set the content
        self.content = bits
    
    
    @classmethod
    def from_hex(cls, s):
        """Creates a new collection from a hexidecimal string.
        
        Args:
            s (str): A hexidecimal string to ingest to the
                collection.
        
        Return:
            BitCollection: new instance.
        
        Raises:
            ValueError: s isn't a valid hexidecimal number.
        
        """
        # Convert it from hex
        content = bytearray.fromhex(s)
        
        # Return the new collection
        return cls(content=content)
    
    
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
        if url_safe:
            s = s.replace('-','+').replace('_','/')
        s += '=='
        
        # Convert it from hex
        content = bytearray(base64.b64decode(s))
        
        # Return the new collection
        return cls(content=content)
    
    
    @classmethod
    def from_int(cls, i, bits):
        """Creates a new collection from a base64 string.
        
        Args:
            i (int): An integer to encode into bits.
            bits (int): Number of bits to assign this integer to.
        
        Return:
            BitCollection: new instance.
            
        """
        # Instantiate here
        obj = cls()
        
        # Manually assign the bitarray
        obj.content = bitarray(int_to_binstr(i, bits=bits))
        
        # Return the new collection
        return obj
    
    
    def length(self):
        """Return the number of bits stored in the object."""
        if not self.content:
            return 0
        return self.content.length()
    
    
    def insert_bitarray(self, b, position):
        """Insert bits into this collection at the given positions.
        
        Args:
            b (bytearray): Content to insert.
            positions (list): The positions to insert bits into the
                collection.
        
        """
        # Roll through each position.
        for j, position in enumerate(positions):
            
            # Put the value into this collection
            self.content.insert(position, b[j])
    
    
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
        
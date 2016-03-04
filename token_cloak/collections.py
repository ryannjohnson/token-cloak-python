import base64
import binascii
from bitarray import bitarray

from .exceptions import ConfigError
from .utils import int8_to_binstr


class BitCollection:
    """Object to hold and manipulate byte arrays.
    
    These collections will be the interface between token data and
    bits that need to be injected and extracted from the data.
    """
    
    def __init__(self, content=None, bit_length=None):
        """Make a new collection out of a bytearray.
        
        Args:
            content (bytearray): Source to create collection from.
            bit_length (Optional[int]): Set the initial bit length.
        """
        # Setup the input.
        b = bytearray([])
        if content:
            if not isinstance(content, bytearray):
                raise ConfigError('content must be a bytearray')
            b = content
        
        # Create the blank bit array.
        a = bitarray()
        
        # Populate it with the bytearray info.
        for c in b:
            d = int8_to_binstr(c)
            a += bitarray(d)
        self.content = bitarray(a)
    
    
    @classmethod
    def from_hex(cls, s, bits=None):
        """Creates a new collection from a hexidecimal string.
        
        Args:
            s (str): A hexidecimal string to ingest to the
                collection.
            bits (Optional[int]): Number of bits to assign this hex to.
                This will be useful for figuring out how many bytes to
                use when injecting and extracting individual bits.
        
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
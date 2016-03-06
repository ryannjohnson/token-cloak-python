import base64
import binascii
from bitarray import bitarray

from .exceptions import ConfigError
from .utils import (
        base64_to_bitarray, bitarray_to_base64, bitarray_to_hex,
        bitarray_to_int, bitarray_to_str, hex_to_bitarray, int_to_bitarray,
        str_to_bitarray)


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
        
        Return:
            BitCollection: new instance.
        
        """
        return cls(bitarray().frombytes(b))
    
    
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
        return cls(hex_to_bitarray(s))
    
    
    @classmethod
    def from_int(cls, i, bits):
        """Creates a new collection from a base64 string.
        
        Args:
            i (int): An integer to encode into bits.
            bits (int): Number of bits to assign this integer to.
        
        Return:
            BitCollection: new instance.
            
        """
        return cls(int_to_bitarray(i, bits=bits))
    
    
    @classmethod
    def from_str(cls, s, codec):
        """Creates a new collection from a string.
        
        Args:
            s (str): A string to encode into bits.
            codec (str): Method of encoding.
        
        Return:
            BitCollection: new instance.
            
        """
        return cls(str_to_bitarray(s, codec=codec))
    
    
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
        return bits.tobytes()
    
    
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
        for j, position in enumerate(positions):
            
            # Get the bit from this collection
            bit = self.content.pop(position)
            
            # Add to the output
            output |= bit << j
        
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
    
    
    def extract_str(self, positions, codec):
        """Extract bits from this collection at the given positions.
        
        Args:
            positions (list): The positions to extract bits from the
                collection.
            codec (str): Method of decoding.
        
        Returns:
            str: base64 encoded.
        
        """
        # Extract the bits
        bits = self.extract_bitarray(positions=positions)
        
        # Convert to str via the codec
        return bitarray_to_str(bits, codec=codec)
    
    
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
        bits = bitarray().frombytes(b)
        
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
    
    
    def insert_str(self, s, positions, codec):
        """Insert string into this collection at the given positions.
        
        Args:
            s (str): Hexadecimal to insert.
            positions (list): The positions to insert bits into the
                collection.
            codec (str): Method of encoding. Examples include 'ascii'
                and 'utf-8'.
        
        """
        bits = str_to_bitarray(s, codec=codec)
        self.insert_bitarray(bits, positions=positions)
    
    
    def length(self):
        """Return the number of bits stored in the object."""
        if not self.content:
            return 0
        return self.content.length()
    
    
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
    
    
    def to_str(self, codec):
        """Express this collection as a string.
        
        Args:
            codec (str): Method of decoding.
        
        Returns:
            str: decoded with the given codec.
        
        """
        return bitarray_to_str(self.content, codec=codec)
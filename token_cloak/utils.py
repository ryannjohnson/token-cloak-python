import base64
import binascii
from bitarray import bitarray
import random


def bitarray_to_base64(b, url_safe=False):
    """Convert a bitarray to a base64 encoded string."""
    # Get the bytes
    bytes_ = b.tobytes()
    
    # Convert it to a string
    string = binascii.b2a_base64(bytes_).decode('ascii').rstrip('\n')
    if strip_padding:
        string = string.rstrip('=')
    
    # Make it url-safe
    if url_safe:
        string = string.replace('+','-').replace('/','_')
    
    # Return the string
    return string


def bitarray_to_hex(b):
    """Convert a bitarray to a hexidecimal string."""
    bytes_ = b.tobytes()
    return binascii.hexlify(bytes_)


def bitarray_to_int(b):
    """Convert a bitarray to an integer."""
    return int(b.to01(), 2)


def bitarray_to_str(b, codec):
    """Convert at bitarray to a string.
    
    Args:
        codec (str): How to decode the bits. Examples include 'ascii'
            and 'utf-8'.
    
    Returns:
        str: made from the decoded bytes from the bits.
    
    """
    return b.tobytes().decode(codec)


def base64_to_bitarray(s, url_safe=False):
    """Convert a base64 string to a bitarray.
    
    Args:
        s (str): Base64 encoded string.
        url_safe (bool): Whether to substitute '-_' with '+/'.
    
    Returns:
        bitarray: made from the base64 string.
    
    """
    # First, make sure the b64 is properly padded and formatted
    if url_safe:
        s = s.replace('-','+').replace('_','/')
    s += '=='
    
    # Decode it
    bytes_ = base64.b64decode(s)
    return bitarray().frombytes(bytes_)


def int_to_bitarray(i, bits):
    """Convert integer to a bitarray.
    
    Args:
        i (int): Value to convert.
        bits (int): Number of bits for this integer.
    
    Returns:
        str: binary representation of the integer.
    
    """
    output = bitarray()
    for j in range(0,bits):
        bit = (i & (1 << j)) >> j
        output.insert(0, bit)
    return output
    

def hex_to_bitarray(s):
    """Convert hexidecimal string into a bitarray."""
    bytes_ = binascii.unhexlify(s)
    return bitarray().frombytes(bytes_)


def int_to_binstr(i, bits):
    """Convert integer to a '01' string.
    
    Args:
        bits (int): Number of bits for this integer.
    
    Returns:
        str: binary representation of the integer.
    
    """
    output = ''
    for j in range(0,bits):
        bit = (i & (1 << j)) >> j
        output = str(bit) + output
    return output


def str_to_bitarray(s, codec):
    """Convert a string to a bitarray.
    
    Args:
        codec (str): How to encode the string into bits. Examples
            include 'ascii' and 'utf-8'.
    
    Returns:
        bitarray: made from the input string.
    
    """
    return bitarray().frombytes(s.encode(codec))


def insert_bits(source, insert, positions):
    """Distribute bits from the inserted value into the source.
    
    This function will insert each bit sequentially, meaning that as
    bits are inserted, they will offset the position of later bits.
    The result will affect the position of all existing and added bits
    on each iteration.
    
    Args:
        source (int): Data in integer form to have bits spliced in.
        insert (int): Data to put into the source.
        positions (list): Ordered integers for splicing data into the
            source. Each number is iterated through in order.
        
    Returns:
        Integer representing the resulting data.
    
    """
    # Figure out the length for managing the top bit shifting
    length = source.bit_length()
    
    # Each position also has an index (for the insert)
    for i, position in enumerate(positions):
        
        # Make sure the string is always as long as the positions
        length = max(length, position)
        
        # Create the top and bottom buns
        bottom_mask = 2**position - 1
        top_mask = (2**(length + i + 1) - 1) ^ bottom_mask
        
        # Get the bit we'll insert
        insert_bit = (2**i & insert) >> i
        
        # Open up the buns and insert the burger
        source = ((top_mask & source) << 1) | (source & bottom_mask)
        source |= insert_bit << (position)
        
    # Return the full quarter-pounder
    return source


def extract_bits(source, positions):
    """Get information from the source data based on bit positions.
    
    This function will extract each bit sequentially, meaning that as
    bits are removed, they will offset the position of later bits. The
    result will affect the osition of all existing and added bits on
    each iteration.
    
    Args:
        source (int): Data to extract information from.
        positions (list): Ordered integers indicating the locations of
            bits to extract. Extraction will cascade and affect the
            location of later bits.
        
    Returns:
        source (int): Source after extraction.
        extracted (int): Data that was extracted.
    
    """
    # Figure out the length for managing the bit shifting
    length = source.bit_length()
    positions_length = len(positions) - 1
    
    # Get the result ready
    extracted = 0
    
    # Each position also has an index (for the insert)
    for i, position in enumerate(positions):
        
        # Create the top and bottom buns
        bottom_mask = 2**position - 1
        top_mask = ((2**(length - i + 1) - 1) - 2**position) ^ bottom_mask
        
        # Extract a patty
        prize_bit = (2**position & source) >> position
        extracted |= prize_bit << (positions_length - i)
        
        # Collapse the buns without the burger
        source = ((top_mask & source) >> 1) | (source & bottom_mask)
        
    # Return the buns and patties seperately
    return source, extracted
    

def int_to_b64(i, url_safe=False, strip_padding=False):
    """Convert an int value into a base64 string.
    
    Args:
        i (int): The value to convert.
        url_safe (bool): Whether to substitute '+/' with '-_'.
        strip_padding (bool): Whether to remove trailing '='s.
    
    Returns:
        b64 (str): Base64 encoded (and padded) string.
    
    """
    # First, pack the int to some bytes
    b = pack_bigint(i)
    
    # Convert it to a string
    b64 = binascii.b2a_base64(b).decode('ascii').rstrip('\n')
    if strip_padding:
        b64 = b64.rstrip('=')
    
    # Make it url-safe
    if url_safe:
        b64 = b64.replace('+','-').replace('/','_')
    return b64


def b64_to_int(b64, url_safe=False):
    """Convert a base64 string into its integer form.
    
    Args:
        b64 (str): Base64 encoded string.
        url_safe (bool): Whether to substitute '-_' with '+/'.
        
    Returns:
        i (int): Integer or long.
    
    """
    # First, make sure the b64 is properly padded and formatted
    if url_safe:
        b64 = b64.replace('-','+').replace('_','/')
    b64 += '=='
    
    # Decode it
    s = base64.b64decode(b64)
    
    # Return the int
    return unpack_bigint(s)


def pack_bigint(i):
    """Packs an integer into a byte array.
    
    Args:
        i (int): The integer to pack.
        
    Returns:
        ba (bytearray): Represents the input integer.
        
    Source:
        http://stackoverflow.com/questions/14764237/how-to-encode-a-long-in-base64-in-python#14764681
    
    """
    ba = bytearray()
    while i:
        ba.append(i & 0xFF)
        i >>= 8
    return ba


def unpack_bigint(ba):
    """Unpacks an integer from a byte array.
    
    Args:
        ba (bytearray|bytes|str): Reprents an integer value.
    
    Returns:
        i (int): The integer representing the input.
    
    Source:
        http://stackoverflow.com/questions/14764237/how-to-encode-a-long-in-base64-in-python#14764681
    
    """
    ba = bytearray(ba)
    i = 0
    for index, value in enumerate(ba):
        i += (1 << (index * 8)) * value
    return i
    

def single_iterator_to_list(iterator):
    """Ride out an iterator and put elements in a list."""
    output = []
    for i in iterator:
        output.append(i)
    return output

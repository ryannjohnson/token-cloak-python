import base64
import binascii
from bitarray import bitarray


def bitarray_to_base64(b, url_safe=False):
    """Convert a bitarray to a base64 encoded string."""
    # Get the bytes
    bytes_ = b.tobytes()
    
    # Convert it to a string
    string = binascii.b2a_base64(bytes_).decode('ascii').rstrip('\n')
    mod = len(string) % 3
    if mod:
        string += '=' * (3 - mod)
    
    # Make it url-safe
    if url_safe:
        string = string.replace('+','-').replace('/','_')
    
    # Return the string
    return string


def bitarray_to_hex(b):
    """Convert a bitarray to a hexidecimal string."""
    bytes_ = b.tobytes()
    s = binascii.hexlify(bytes_).decode('ascii')
    if b.length() % 8 and not (b.length() % 4):
        return s[:-1]
    return s


def bitarray_to_bytes(b):
    """Convert a bitarray to bytes."""
    return b.tobytes()


def bitarray_to_int(b):
    """Convert a bitarray to an integer."""
    if not len(b):
        return 0
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
    a = bitarray()
    a.frombytes(bytes_)
    return a


def bytes_to_bitarray(b):
    """Convert bytes into a bitarray."""
    a = bitarray()
    a.frombytes(b)
    return a


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
    padded = False
    if len(s) % 2:
        padded = True
        s += '0'
    bytes_ = binascii.unhexlify(s)
    a = bitarray()
    a.frombytes(bytes_)
    if padded:
        for i in range(4):
            a.pop()
    return a


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
    
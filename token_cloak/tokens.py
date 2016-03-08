import base64
import copy
import os
import random
import re

from .collections import BitCollection, SecretKeyCollection
from .exceptions import ConfigError
from .random import MT19937
from .utils import (
        b64_to_int, chunk_string, extract_bits, insert_bits,
        int_to_b64, single_iterator_to_list)


class TokenLayer:
    """Provides a common interface for several token layer types."""
    
    TYPES = [
        'int',
        'bytes',
        'str',
        'hex',
        'base64',
    ]
    """The list of valid types."""
    
    def __init__(self, d):
        """Takes a dictionary of settings and ingests it as a layer."""
        
        # Setup variable for later.
        self.value = None
        
        # Must be a dictionary.
        if not isinstance(d, dict):
            raise ConfigError('layers must each be a dict')
        self.config = d
        
        # What is this layer's type?
        self.type = d.get('type', None)
        if self.type not in self.TYPES:
            err = 'layer type must be in %s' % ', '.join(self.TYPES)
            raise ConfigError(err)
        
        # Init the bits.
        self.bits = d.get('bits', None)
        if self.bits != None and not isinstance(bits, int):
            raise ConfigError('layer bits key must be a positive int')
        
        # Init the length.
        self.length = d.get('length', None)
        if not length and not self.bits:
            raise ConfigError('layer bits key must be a positive int')
        if length and not isinstance(length, int) or length < 1:
            raise ConfigError('layer length must be a positive int')
        
        # Ints require bits.
        if self.type == 'int':
            if not self.bits:
                raise ConfigError('layer int bits key must be a positive int')
            self.length = self.bits
        
        # Bytes are 8 bits each.
        elif self.type == 'bytes':
            if self.bits:
                if (self.bits % 8) != 0:
                    raise ConfigError('layer bytes bits must be divisible by 0')
                self.length = self.bits // 8
            else:
                self.bits = self.length * 8
        
        # Hex are 16 bits per character.
        elif self.type == 'hex':
            if self.bits:
                if (self.bits % 16) != 0:
                    raise ConfigError('layer hex bits must be divisible by 16')
                self.length = self.bits // 16
            else:
                self.bits = self.length * 16
        
        # Base64 are 24 bits per 3 characters.
        elif self.type == 'base64':
            if self.bits:
                if (self.bits % 24) != 0:
                    err = 'layer base64 bits must be divisible by 24'
                    raise ConfigError(err)
                self.length = self.length // 24
            else:
                if (self.length % 3) != 0:
                    err = 'layer base64 length must be divisible by 3'
                    raise ConfigError(err)
                self.bits = self.length * 24
            
            # Set the config for url safe.
            self.config['url_safe'] = self.config.get('url_safe', False)
        
        # String?
        elif self.type == 'str':
            
            # Requires a codec.
            config = d.get('codec', None)
            self.config['codec'] = config
            if not codec or not isinstance(codec, str):
                raise ConfigError('layer str codec is required')
            
            # Test the codec to get its length.
            bytes_ = 'a'.encode(codec) # May raise error
            bits_per_length = len(bytes_) * 8
            
            # Figure out bits and length.
            if self.bits:
                if (self.bits % bits_per_length) != 0:
                    err = 'layer str bits is incompatible with %s' % codec
                    raise ConfigError(err)
                self.length = self.bits // bits_per_length
            else:
                self.bits = self.length * bits_per_length
        
        # Type doesn't count.
        else:
            raise ConfigError('invalid layer type')
        
        # Every type has the optional 'positions' key
        self.positions = None
        positions = d.get('positions', None)
        if positions:
            
            # Make sure the positions are syntacticly valid
            err = 'positions must be a list of non-negative ints'
            if not isinstance(positions, list):
                raise ConfigError(err)
            for value in positions:
                if not isinstance(value, int) or value < 0:
                    raise ConfigError(err)
            
            # Do the number of positions match the number of bits?
            if len(poisitions) != self.bits:
                raise ConfigError('number of layer positions must match bits')
            
            # Positions is valid
            self.positions = positions
    
    
    def to_bitcollection(self, v):
        """Get the BitCollection for this layer."""
        
        # Is it an int?
        if self.type == 'int':
            if not isinstance(v, int):
                raise ValueError('layer value must be an int')
            if v.bit_length() > self.bits:
                raise ValueError('layer value is too many bits')
            return BitCollection.from_int(v, bits=self.bits)
        
        # Is it bytes?
        if self.type == 'bytes':
            if not isinstance(v, bytes):
                raise ValueError('layer value must be bytes')
            if len(v) != self.length:
                raise ValueError('layer value is incorrect length')
            return BitCollection.from_bytes(v)
        
        # Is it string?
        if self.type in ['hex','base64','str']:
            if not isinstance(v, str):
                raise ValueError('layer value must be str')
            if len(v) != self.length:
                raise ValueError('layer value is incorrect length')
            if self.type == 'hex':
                return BitCollection.from_hex(v)
            if self.type == 'base64':
                return BitCollection.from_base64(
                        v, url_safe=self.config.get('url_safe', False))
            if self.type == 'str':
                return BitCollection.from_str(
                        v, codec=self.config.get('codec', None))
        
        # Something failed here, which should be impossible.
        raise ConfigError('unable to create BitCollection')
    
    
    def from_bitcollection(self, b):
        """Convert to original format."""
        if not self.value:
            return None
        if self.type == 'int':
            return b.to_int()
        if self.type == 'bytes':
            return b.to_bytes()
        if self.type == 'hex':
            return b.to_hex()
        if self.type == 'base64':
            return b.to_base64(url_safe=self.config.get('url_safe'))
        if self.type == 'str':
            return b.to_str(codec=self.config.get('codec'))
        raise ConfigError('unable to convert to original format')
    

class Token:
    """Generate and encode tokens based on ordered parameters. 
    
    TokenGenerator methods affect how the final token will be created.
    Some methods overwrite their previous values, while others append
    to ordered lists.
    
    A token option can optionally be given a single config dictionary
    with all the necessary parameters. This is an easier method of
    sharing token configurations between functions and modules.
    
    A sample config could be stored as and submitted as the following:
        config = {
            "secret": "the length of this should be very long",
            "random_bits": 512,
            "seed_bits": 4,
            "layers": [
                {
                    'type': 'int',
                    'bits': 64, # 64 bits
                },
                {
                    'type': 'str',
                    'codec': 'ascii',
                    'length': '12', # 96 bits (ascii = 8 bits per char)
                },
                {
                    'type': 'int',
                    'bits': 5,
                    'positions': [1,5,2,3,5], # Manual bit positions
                },
            ],
        }
    
    Here is a sample usage:
        >>> t1 = Token(config)
        >>> public_token, stored_token1 = t1.encode(1,2,3)
        >>> type(public_token), type(stored_token1)
        (<class 'str'>, <class 'int'>)
        >>> t2 = Token(config)
        >>> stored_token2, a, b, c = t2.decode(public_token)
        >>> stored_token1 == stored_token2
        True
    
    """
    
    def __init__(self, config=None):
        """Set default object properties."""
        
        # The secret string to use for predictable randomness.
        self.secret_key = None
        
        # Number of bits saying how many automatic positions exist.
        self.seed_bits = 4
        
        # What should the random token look like?
        self.random_bits = 512
        
        # Values getting spliced into the public token.
        self.layers = []
        
        # Before and after tokens.
        self.public_token = None
        self.stored_token = None
        
        # Is loads here?
        self.config = {}
        if config:
            self.config(config)
        
    
    def config(self, config):
        """Ingest a config dictionary.
        
        Raises:
            ConfigError: layers must be lists or ints.
        
        """
        # Keep this config.
        self.config = config
        
        # Ingest the secret used to seed everything.
        secret = config.get('secret_key', None)
        if secret:
            if not isinstance(secret, str):
                raise ConfigError('secret key must be a string')
            self.secret_key = secret
        
        # Might have to use global secret if available
        else:
            from token_cloak import secret_key
            if not secret_key:
                raise ConfigError('secret key is not set')
            self.secret_key = secret_key
        
        # Get the secret key collection going.
        self.secret_key_collection = SecretKeyCollection(self.secret_key)
        
        # Determines the length of stored token.
        self.stored_token = None
        random_bits = config.get('random_bits', None)
        if random_bits:
            
            # Reset the stored token
            self.stored_token = None
            
            # Is it a direct injection?
            if isinstance(random_bits, BitCollection):
                self.stored_token = random_bits
                self.stored_token_bits = self.stored_token.length
            
            # Is it just a length for random generation?
            else:
                if not isinstance(random_bits, int) or random_bits < 0:
                    raise ConfigError('random bits must be a non-negative int')
                
                # Generate the token now
                self.stored_token_bits = random_bits
        
        # Determines how many possible seeds there can be.
        seed_bits = config.get('seed_bits', None)
        if seed_bits:
            if not isinstance(seed_bits, int) or seed_bits < 0:
                raise ConfigError('seed bits must be a non-negative int')
            self.seed_bits = seed_bits
        
        # Ingest the layers sequence and sizes.
        self.layers = []
        if config.get('layers', None):
            if not isinstance(config.get('layers'), list):
                raise ConfigError('layers must be a list')
            
            # Ingest layers as TokenLayers.
            for row in config.get('layers'):
                self.layers.append(TokenLayer(row)) # Raises ConfigError
    
    
    def encode(self, *args):
        """Make the public token based on the input values.
        
        If arguments are supplied with this method, then they will
        override any current settings on the object.
        
        Returns:
            BitCollection: public token.
        
        Raises:
            ConfigError: number of args doesn't match number of layers.
        
        """
        # Generate a new stored token.
        if self.stored_token_bits > 0:
            bytes_ = os.urandom(self.stored_token_bits // 8)
            self.stored_token = BitCollection.from_bytes(bytes_)
        else:
            self.stored_token = BitCollection()
        
        # Start the new public token.
        self.public_token = copy.deepcopy(self.stored_token)
        
        # Ensure the input matches
        if len(args) != len(self.layers):
            raise ConfigError('number of args doesn\'t match number of layers')
        
        # Are there any layers?
        if not self.layers:
            return self.public_token
        
        # How many layers need seeds?
        need_seeds = 0
        for layer in self.layers:
            if not layer.positions:
                need_seeds += 1
        
        # Decide on predictable seed positions up front
        seed_sources = []
        if need_seeds > 0:
            for chunk in self.secret_key_collection.chunk(need_seeds):
                seed_sources.append(chunk)
            seed_sources = seed_sources[::-1]
        
        # Go through each layer in order
        for index, layer in enumerate(self.layers):
            
            # Does this layer have positions?
            layer_seed_seed = None
            layer_seed_value = None
            layer_positions = layer.positions
            if not positions:
                
                # Get the seed prepared.
                layer_seed_seed = seed_sources.pop()
                layer_seed_value = random.randint(0, (2 ** self.seed_bits) - 1)
                
                # Generate the layer positions using the seed.
                layer_positions = self.generate_bit_positions(
                        seed=layer_seed_value,
                        max_position=self.public_token.length,
                        bits=layer.bits)
            
            # Sew in the new bits.
            self.public_token.insert(
                    layer.to_bitcollection(
                            args[index]), positions=layer_positions)
            
            # Was there an automatic seed?
            if layer_seed_seed and layer_seed_value:
                
                # Generate the seed positions.
                seed_positions = self.generate_bit_positions(
                        seed=layer_seed_seed,
                        max_position=self.public_token.length,
                        bits=self.seed_bits)
                
                # Sew in the seed bits.
                self.public_token.insert_int(
                        layer_seed_value, positions=seed_positions)
        
        # All spliced - return self.
        return self
    
    
    def decode(self, token, data_type=None):
        """Decode a token created by this class.
        
        For accurate decoding, it is essential that the input
        parameters used to create the token are provided in the same
        manner as they were for generation.
        
        The main difference is the 'values' attribute will be updated
        with the decoded values from the token.
        
        Args:
            token (str): Base64 encoded public token.
            data_type (Optional[str]): How the token is encoded on a
                data level. Optional if not string or if in config.
        
        Returns:
            If successful, dict. Otherwise, False.
        
        """
        # How is the incoming public token encoded?
        if data_type:
            types = ['base64','bytes','hex','int','str']
            if data_type not in types:
                err = 'data type is not in %s' % ', '.join(types)
                raise ValueError(err)
        
        # Get data_type from somewhere else.
        else:
            data_type = self.config.get('public_token_encoding', None)
        
        # Validate the token on a baseline level
        length_with_pad = self.public_token_bit_length(with_padding=True)
        working_length = self.public_token_bit_length(with_padding=False)
        self.actual_length = working_length
        working_token = self.decode_b64(token, bit_length=length_with_pad)
        if not working_token:
            return none
        
        # No layers?
        if not self.layers:
            
            # Remove the padding
            working_token &= (1 << working_length) - 1
            
            # Return the single stored token
            self.stored_token = working_token
            return self.stored_token
        
        # Get the seed bits from the token
        seed_length = len(self.layers) * self.seed_bits
        positions = single_iterator_to_list(range(1,(seed_length*2)+1,2))
        working_token, final_seeds = extract_bits(
            source=working_token,
            positions=positions[::-1])
        working_length -= seed_length
        
        # Put the seeds into an ordered array
        seeds = []
        for i in range(len(self.layers)):
            offset = i * self.seed_bits
            mask = 2 ** self.seed_bits - 1
            seed = (final_seeds & (mask << offset)) >> offset
            
            # Make sure the seed is valid
            seed_value = settings.TOKEN_VERSIONS.get(seed, None)
            if not seed_value:
                return none
            seeds.append((seed, seed_value,))
        
        # Iterate through layers and get information
        extracted_layers = []
        original_layers = self.layers[::-1]
        seeds = seeds[::-1]
        for index, layer in enumerate(original_layers):
            layer_length = layer[0]
            
            # Adjust the working length
            working_length -= layer_length
            
            # Get the extracted bits
            seed_value = seeds[index][1]
            positions = self.generate_bit_positions(
                    seed_value,
                    max_position=working_length,
                    bits=layer_length)
            working_token, extracted = extract_bits(
                    source=working_token, positions=positions[::-1])
            
            # Add to the extracted layers
            extracted_layers.append((layer_length, extracted,))
        
        # Remove the padding
        working_token &= (1 << working_length) - 1
        
        # Set class variables and get ready to close
        self.stored_token = working_token
        self.layers = extracted_layers[::-1]
        return self.unpack()
        
    
    def set_random_bits(self, num=512):
        """
        Set the number of random bits that get injected into the token.
        
        Since the decoding seeds are built into the front of the
        resulting token, the number of random bits must be at least
        as long as the number of injected value bits.
        """
        # Cast it to integer
        num = int(num)
        
        # Is it divisible by 8?
        mod = num % 8
        if mod:
            num += (8-mod)
        
        # Set it
        self.random_bits = num
        return self
    
    
    def add_layer(self, bit_length, value=None):
        """Add a layer of information to encode into the token.
        
        Args:
            bit_length(int): The number of bits to dedicate to this
                particular value.
            value (int): The value to hide in the token.
        
        """
        self.layers.append((int(bit_length),value,))
        return self
    
    
    def pack(self, *args):
        """
        Given a configuration, set the values according to the input.
        
        Raises:
            ConfigError: number of args doesn't match number of layers.
        
        """
        # Ensure the input matches
        if len(args) != len(self.layers):
            raise ConfigError('number of args doesn\'t match number of layers')
        
        # Create new list of tuples
        new_layers = []
        i = 0
        for bits, value in self.layers:
            new_layers.append((bits, args[i],))
            i += 1
        
        # Update this object's layers
        self.layers = new_layers
        
    
    def unpack(self):
        """
        Get the values from the decoded token as they were inserted.
        
        Returns:
            tuple: Contains all the values from the token, including
                the stored token as the first value.
            
            If decode was unsuccessful, returns tuple of None, as many
            as were expected on success.
        
        """
        # Get all the expected values
        values = []
        for row in self.layers:
            values.append(row[1])
        return (self.stored_token,) + tuple(values)
    
    
    def public_token_bit_length(self, with_padding=None):
        """
        Helper function to calculate supposed bit length for token.
        
        Args:
            with_padding (Optional[str]): Data type to pad for.
        
        Returns:
            int: number of bits expected for the public token.
        
        """
        # How many random bits are there?
        total_bits = self.random_bits
        
        # Do the math for each layer
        if self.layers:
            for layer in self.layers:
                
                # Add bits for included seed
                if not layer.positions:
                    total_bits += self.seed_bits
                
                # Add the number of bits the actual value can be
                total_bits += layer.bits
        
        # Pad it?
        if with_padding:
            mod = total_bits % 6
            if mod:
                total_bits += (6-mod)
            
            # Add an additional 6 now for standardized lengthening
            total_bits += 6
        
        # Return the tally
        return total_bits
        
    
    def encode_b64(self, token=None, bit_length=None):
        """
        Helper function to both pad the raw token and convert it into a
        base64 string.
        
        If no token is provided, then the internal 'stored_token' is
        used instead.
        """
        if not token:
            token = self.stored_token
        if not token:
            return None
            
        # Pad it if necessary
        if bit_length:
            baseline = self.actual_length = bit_length
        else:
            baseline = self.actual_length
        mod = baseline % 6
        if mod:
            baseline += (6 - mod)
        
        # Make the token reach a certain length
        token |= random.randint(0,63) << baseline
        token |= 1 << (baseline + 5)
        
        # Do the actual encoding
        self.public_token = int_to_b64(
                token, url_safe=True, strip_padding=True)
        return self.public_token, self.stored_token
        
    
    @staticmethod
    def generate_bit_positions(seed, max_position, bits):
        """
        Generates an ordered list of integer positions based on the
        provided elements.
        
        Args:
            seed (mixed): Hashable value to create predictable randomness.
            max_position (int): Highest allowed position to generate.
            bits (int): Number of positions needed for this operation.
        
        Returns:
            positions (list): List of integers, denoting the position in
                the public token for bits to reside.
        
        """
        # Seed the randomness according to the seed
        r = MT19937(seed)
        
        # Start generating
        positions = []
        for i in range(bits):
            positions.append(r.rand_int(0, max_position))
        
        # Return the list of integers
        return positions


    def decode_b64(self, token, bit_length=None):
        """
        Runs checks to make sure tokens came from this module.
        
        Args:
            token (str): Raw string from the client.
            bit_length (Optional[int]): Expected length from the token.
        
        Returns:
            Int token if valid, False otherwise.
        
        """
        # Correct characters?
        if not token:
            return False
        matches = re.match(r'^[a-zA-Z0-9\-_]+$', token)
        if not matches:
            return False
        
        # Can it be b64 decoded?
        try:
            token = b64_to_int(token, url_safe=True)
        except:
            return False
        
        # Is is the right length?
        if bit_length and token.bit_length() != bit_length:
            return False
        
        # It passed
        return token

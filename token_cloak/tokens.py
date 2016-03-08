import base64
import binascii
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
        'BitCollection',
        'int',
        'bytes',
        'hex',
    ]
    """The list of valid types."""
    
    def __init__(self, d):
        """Takes a dictionary of settings and ingests it as a layer."""
        
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
        if self.bits != None and not isinstance(self.bits, int):
            raise ConfigError('layer bits key must be a positive int')
        
        # Init the length.
        self.length = d.get('length', None)
        if not self.length and not self.bits:
            raise ConfigError('layer bits key must be a positive int')
        if self.length:
            if not isinstance(self.length, int) or self.length < 1:
                raise ConfigError('layer length must be a positive int')
        
        # Bits and ints require bits.
        if self.type in ['BitCollection','int']:
            if not self.bits:
                err = 'layer %s bits key must be a positive int'
                raise ConfigError(err % self.type)
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
                if (self.bits % 4) != 0:
                    raise ConfigError('layer hex bits must be divisible by 16')
                self.length = self.bits // 4
            else:
                self.bits = self.length * 4
        
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
            if len(positions) != self.bits:
                raise ConfigError('number of layer positions must match bits')
            
            # Positions is valid
            self.positions = positions
    
    
    def to_bitcollection(self, v):
        """Get the BitCollection for this layer."""
        
        # Is it a BitCollection?
        if self.type == 'BitCollection':
            if not isinstance(v, BitCollection):
                raise ValueError('layer value must be a BitCollection')
            if v.length() != self.bits:
                raise ValueError('layer value has incorrect number of bits')
            return v
        
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
        if self.type == 'hex':
            if not isinstance(v, str):
                raise ValueError('layer value must be str')
            if len(v) != self.length:
                raise ValueError('layer value is incorrect length')
            return BitCollection.from_hex(v)
        
        # Something failed here, which should be impossible.
        raise ConfigError('unable to create BitCollection')
    
    
    def from_bitcollection(self, b):
        """Convert to original format."""
        if self.type == 'BitCollection':
            return b
        if self.type == 'int':
            return b.to_int()
        if self.type == 'bytes':
            return b.to_bytes()
        if self.type == 'hex':
            return b.to_hex()
        raise ConfigError('unable to convert to original format')


class TokenResult:
    """Object created from decoding a token.
    
    The Token object only carries configuration information. It's
    resulting collection carries its results.
    """
    
    def __init__(self, private_token=None, public_token=None, layers=None):
        """Populate the collection once with everything it'll ever have.
        
        """
        self.layers = layers
        self.public_token = public_token
        self.private_token = private_token


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
            "secret_key": "the length of this should be very long",
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
        self.stored_token_bits = 0
        
        # Values getting spliced into the public token.
        self.layers = []
        
        # Is config here?
        self.config = {}
        if config:
            self.set_config(config)
        
    
    def set_config(self, config):
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
        self.stored_token_bits = 0
        random_bits = config.get('random_bits', None)
        if random_bits:
            
            # Is it a direct injection?
            if isinstance(random_bits, BitCollection):
                self.stored_token_bits = random_bits
            
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
        # Ensure the input matches
        stored_token = None
        if len(args) != len(self.layers):
            
            # Is there not just one more than before?
            if len(args) != (len(self.layers) + 1):
                err = 'number of args doesn\'t match number of layers'
                raise ConfigError(err)
            
            # The first argument will be treated as a token.
            stored_token = args[0]
            if not isinstance(args[0], BitCollection):
                raise ValueError('token must be a BitCollection')
            
            # Is it the correct length?
            if stored_token.length() != self.stored_token_bits:
                err = 'token must be %d bits long, is currently %d'
                err = err % (self.stored_token_bits, stored_token.length(),)
                raise ValueError(err)
            
            # Adjust the args for proper use.
            args = tuple(list(args)[1:])
        
        # Generate a new stored token.
        if not stored_token:
            if self.stored_token_bits and self.stored_token_bits > 0:
                bits = self.stored_token_bits
                mod = bits % 8
                if mod:
                    bits += (8 - mod)
                bytes_ = os.urandom(bits // 8)
                stored_token = BitCollection.from_bytes(bytes_)
                if mod:
                    for i in range(8 - mod):
                        stored_token.pop()
            else:
                stored_token = BitCollection()
        
        # Start the new public token.
        public_token = copy.deepcopy(stored_token)
        
        # Are there any layers?
        if not self.layers:
            return TokenResult(
                    public_token=public_token,
                    private_token=stored_token)
        
        # Decide on predictable seed positions up front
        seed_sources = []
        need_seeds = self.needed_seeds()
        if need_seeds > 0:
            for chunk in self.secret_key_collection.chunk(need_seeds):
                seed_sources.append(chunk)
            seed_sources = seed_sources[::-1]
        
        # Go through each layer in order
        stored_layers = []
        for index, layer in enumerate(self.layers):
            
            # Does this layer have positions?
            layer_seed_seed = None
            layer_seed_value = None
            layer_positions = layer.positions
            if not layer_positions:
                
                # Get the seed prepared.
                layer_seed_seed = seed_sources.pop()
                layer_seed_value = random.randint(0, (2 ** self.seed_bits) - 1)
                
                # Generate the layer positions using the seed.
                layer_positions = self.generate_bit_positions(
                        seed=layer_seed_value,
                        max_position=public_token.length(),
                        bits=layer.bits)
            
            # Sew in the new bits.
            public_token.insert(
                    layer.to_bitcollection(
                            args[index]), positions=layer_positions)
            
            # Save the content.
            stored_layers.append(args[index])
            
            # Was there an automatic seed?
            if layer_seed_seed:
                
                # Generate the seed positions.
                seed_positions = self.generate_bit_positions(
                        seed=layer_seed_seed,
                        max_position=public_token.length(),
                        bits=self.seed_bits)
                
                # Sew in the seed bits.
                public_token.insert_int(
                        layer_seed_value, positions=seed_positions)
        
        # All spliced - return results.
        return TokenResult(
                public_token=public_token,
                private_token=stored_token,
                layers=stored_layers)
    
    
    def decode(self, token, data_type=None, **kwargs):
        """Decode a token created by this class.
        
        For accurate decoding, it is essential that the input
        parameters used to create the token are provided in the same
        manner as they were for generation.
        
        The main difference is the 'values' attribute will be updated
        with the decoded values from the token.
        
        Args:
            token (mixed): public token in a variety of possible types.
            data_type (Optional[str]): How the token is encoded on a
                data level. Optional if not string or if in config.
        
        Returns:
            If successful, dict. Otherwise, None.
        
        """
        # Get data_type from somewhere else.
        if not data_type:
            data_type = self.config.get('public_token_type', None)
        
        # Start with the expected length.
        expected_length = self.public_token_bit_length()
        bit_remainder = 0
        
        # Put the token into a BitCollection based on data_type.
        if not data_type:
            if not isinstance(token, BitCollection):
                raise ValueError('token\'s data type does not match')
            public_token = token
        
        # Decode from base64.
        elif data_type == 'base64':
            try:
                public_token = BitCollection.from_base64(
                        token, url_safe=kwargs.get('url_safe', None))
            except binascii.Error:
                return None
            # bit_remainder = expected_length % 6
        
        # Decode from bytes.
        elif data_type == 'bytes':
            public_token = BitCollection.from_bytes(token)
            print(public_token.length())
            bit_remainder = 8 - (expected_length % 8)
        
        # Decode from hex.
        elif data_type == 'hex':
            public_token = BitCollection.from_hex(token)
            bit_remainder = 4 - (expected_length % 4)
        
        # Decode from int.
        elif data_type == 'int':
            if token.bit_length() > self.public_token_bit_length():
                return None
            public_token = BitCollection.from_int(
                    token, bits=self.public_token_bit_length())
        
        # Decode from str.
        elif data_type == 'str':
            public_token = BitCollection.from_str(
                    token, codec=kwargs.get('codec', None))
            sample_byte = 'a'.encode(kwargs.get('codec', None))
            b2 = sample_byte * 8
            bit_remainder = b2 - (expected_length % b2)
        
        # Invalid type.
        else:
            raise ValueError('invalid data_type')
        
        # Adjust if a remainder exists.
        for i in range(bit_remainder):
            public_token.pop()
        
        # Validate the token by its length.
        if expected_length != public_token.length():
            print('Expected length:', expected_length)
            print('Token length:', public_token.length())
            return None
        
        # Setup the stored token.
        stored_token = copy.deepcopy(public_token)
        
        # Are there layers?
        if not self.layers:
            return TokenResult(
                    public_token=public_token,
                    private_token=stored_token)
        
        # Setup for peeling away layers.
        stored_layers = []
        seed_sources = []
        need_seeds = self.needed_seeds()
        if need_seeds > 0:
            for chunk in self.secret_key_collection.chunk(need_seeds):
                seed_sources.append(chunk)
        
        # Start off with the layers!
        for index, layer in enumerate(self.layers[::-1]):
            
            # Does it have a seeded position?
            layer_seed_seed = None
            layer_seed_value = None
            layer_positions = layer.positions
            if not layer_positions:
                
                # Get the seed from the token.
                layer_seed_seed = seed_sources.pop()
                seed_positions = self.generate_bit_positions(
                        seed=layer_seed_seed,
                        max_position=stored_token.length() - self.seed_bits,
                        bits=self.seed_bits)
                
                # Extract in the seed bits.
                layer_seed_value = stored_token.extract_int(
                        positions=seed_positions[::-1])
                
                # Generate the layer positions using the seed.
                layer_positions = self.generate_bit_positions(
                        seed=layer_seed_value,
                        max_position=stored_token.length() - layer.bits,
                        bits=layer.bits)
                
            # Get the layer value from the token based on format.
            layer_value = stored_token.extract(
                    positions=layer_positions[::-1])
            
            # Store the value away as its original datatype.
            stored_layers.append(layer.from_bitcollection(layer_value))
        
        # Reverse the stored_layers in order to match how layers are added.
        stored_layers = stored_layers[::-1]
        
        # All done!
        return TokenResult(
                public_token=public_token,
                private_token=stored_token,
                layers=stored_layers)
    
    
    def needed_seeds(self):
        """Calculates number of layer seeds needed to be generated."""
        need_seeds = 0
        for layer in self.layers:
            if not layer.positions:
                need_seeds += 1
        return need_seeds
    
    
    def public_token_bit_length(self):
        """
        Helper function to calculate supposed bit length for token.
        
        Args:
            with_padding (Optional[str]): Data type to pad for.
        
        Returns:
            int: number of bits expected for the public token.
        
        """
        # How many random bits are there?
        total_bits = self.stored_token_bits
        
        # Do the math for each layer
        if self.layers:
            for layer in self.layers:
                
                # Add bits for included seed
                if not layer.positions:
                    total_bits += self.seed_bits
                
                # Add the number of bits the actual value can be
                total_bits += layer.bits
        
        # Return the tally
        return total_bits
        
    
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
    
import base64
from django.conf import settings
import os
import random
import re

from .exceptions import ConfigError
from .utils import (
        b64_to_int, extract_bits, insert_bits,
        int_to_b64, single_iterator_to_list)


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
            "layers": [64,44,12],
            "version": {
                "bits": 6,
                "value": 1,
            },
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
        
        # Version values
        # These are used to define the token version amongst other
        # encoding styles.
        self.version_value = 1
        self.version_bits = 6
        
        # The secret string to use for seeding
        self.secret = None
        
        # Global seed bit length
        self.seed_bits = 4
        
        # Used in the random token generator
        self.random_bits = self.set_random_bits(512)
        
        # Values getting spliced into the pulic token
        self.layers = []
        
        # Results
        self.public_token = ''
        self.stored_token = None
        self.actual_length = 0
        
        # Is loads here?
        if config:
            self.config(config)
        
    
    def encode(self, *args):
        """Shortcut for self.generate()."""
        return self.generate(*args)
    
    
    def generate(self, *args):
        """Make the token based on the input values.
        
        If arguments are supplied with this method, then they will
        override any current settings on the object.
        
        Returns:
            str: public token.
            int: stored token.
        
        Raises:
            ConfigError: number of args doesn't match number of layers.
        
        """
        # Override existing parameters if available
        if args:
            self.pack(*args) # ConfigError
        
        # Start by generating the stored token
        self.stored_token = int.from_bytes(
                os.urandom(self.random_bits // 8), byteorder='big')
        
        # Anything else?
        if not self.layers:
            return self.encode_b64(
                    self.stored_token, bit_length=self.random_bits)
        
        # Pad it for the generation process
        current_length = self.random_bits
        working_token = self.stored_token | 1 << current_length
        
        # Decide on each seed for the information encoding
        seeds = []
        for i in range(len(self.layers)):
            seed = random.randint(0,2 ** self.seed_bits - 1)
            seed_value = settings.TOKEN_VERSIONS.get(seed)
            seeds.append((seed, seed_value,))
        
        # Go through each layer in order
        for index, layer in enumerate(self.layers):
            layer_length, layer_value = layer
            
            # Generate the bit positions
            seed_value = seeds[index][1]
            bits = layer_length
            positions = self.generate_bit_positions(
                    seed_value, max_position=current_length, bits=bits)
            
            # Sew in the new bits
            working_token = insert_bits(
                    source=working_token,
                    insert=layer_value,
                    positions=positions)
            
            # Assuming another round, append the bit length
            current_length += bits
        
        # Concat the seeds for splicing
        final_seeds = 0
        seed_length = 0
        for i, seed in enumerate(seeds):
            seed_length += self.seed_bits
            final_seeds |= seed[0] << (i*self.seed_bits)
        
        # Sew in the seed bits
        positions = single_iterator_to_list(range(1,(seed_length*2)+1,2))
        working_token = insert_bits(
                source=working_token,
                insert=final_seeds,
                positions=positions)
        current_length += seed_length
        
        # Now insert the tokening seed
        positions = single_iterator_to_list(range(self.version_bits))
        public_token = insert_bits(
                source=working_token,
                insert=self.version_value,
                positions=positions)
        current_length += self.version_bits
        
        # Take away that space preserver
        working_token &= (1 << current_length) - 1
        
        # All spliced - encode it and return
        return self.encode_b64(public_token, bit_length=current_length)
    
    
    def decode(self, token):
        """Decode a token created by this class.
        
        For accurate decoding, it is essential that the input
        parameters used to create the token are provided in the same
        manner as they were for generation.
        
        The main difference is the 'values' attribute will be updated
        with the decoded values from the token.
        
        Args:
            token (str): Base64 encoded public token.
        
        Returns:
            int: Stored token from the public token.
            *mixed: N number of layers as is denoted by the config.
            
            Tuple of None as long as N+1 if token is invalid.
        
        Note:
            The working_token padding is left on the token until the
            end of the decoding process. This is intentional so that
            the meaningful bit positions are preserved until the very
            end.
        
        """
        # Prepare for failure
        none = tuple([None for i in range(len(self.layers)+1)])
        if len(none) == 1:
            none = None
        
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
        
        # Get the version from the token
        positions = single_iterator_to_list(range(self.version_bits))
        working_token, version = extract_bits(
                source=working_token,
                positions=positions[::-1])
        working_length -= self.version_bits
        
        # Must match the designated version
        if version != self.version_value:
            return none
        
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
        
    
    def config(self, config=None):
        """Ingest a config dictionary. The 'token' key is optional.
        
        If no config is supplied, this method does nothing.
        
        Example dictionary:
            {
                "random_bits": 1024,
                "seed_bits": 4,
                "layers":[
                    64,
                    [32, 54321]
                ],
                "token": "messy-token-string"
            }
        
        Raises:
            ConfigError: layers must be lists or ints.
        
        """
        # If nothing, exit gently.
        if not config:
            return
        
        # Ingest the secret used to seed everything.
        if config.get('secret', None):
            self.secret = config.get('secret')
        
        # Ingest the random bits, designating the length of raw token.
        if config.get('random_bits', None):
            self.set_random_bits(config.get('random_bits'))
        
        # Ingest seed bits, which determines how many possible seeds
        # there can be.
        if config.get('seed_bits', None):
            self.seed_bits = config.get('seed_bits')
        
        # Ingest the layers sequence and sizes.
        self.layers = []
        if config.get('layers', None):
            if not isinstance(config.get('layers'), list):
                raise ConfigError('layers must be a list')
            for row in config.get('layers'):
                if isinstance(row, list) or isinstance(row, tuple):
                    if len(row) not in [1,2]:
                        err = 'layer lists must have one or two values'
                        raise ConfigError(err)
                    for value in row:
                        if not isinstance(value, int):
                            err = 'layer lists may only contain ints'
                            raise ConfigError(err)
                    self.layers.append((row[0], row[1],))
                elif isinstance(row, int):
                    self.layers.append((row, None,))
                else:
                    raise ConfigError('layers must be lists or ints')
        
        # Ingest a public token, although this shouldn't be required.
        if config.get('token', None):
            self.public_token = config.get('token', None)
        
        # Ingest the version, essential to allowing future growth.
        if config.get('version', None):
            if not isinstance(config.get('version'), dict):
                raise ConfigError('version must be a dict')
            version = config.get('version')
            self.version_bits = version.get('bits', None)
            self.version_value = version.get('value', None)
            if self.version_bits == None or self.version_value == None:
                raise ConfigError('version must contain both bits and value')
    
    
    def public_token_bit_length(self, with_padding=True):
        """
        Helper function to calculate supposed bit length for token.
        """
        # How many random bits are there?
        total_bits = self.random_bits
        
        # Do the math for each layer
        if self.layers:
            for layer in self.layers:
                
                # Add bits for included seed
                total_bits += self.seed_bits
                
                # Add the number of bits the actual value can be
                total_bits += layer[0]
            
            # Add the version
            total_bits += self.version_bits
        
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
        
    
    def generate_bit_positions(self, seed, max_position, bits):
        """
        Generates an ordered list of integer positions based on the
        provided elements.
        
        Args:
            seed (int): To create predictable randomness.
            max_position (int): Highest allowed position to generate.
            bits (int): Number of positions needed for this operation.
        
        Returns:
            positions (list): List of integers, denoting the position in
                the public token for bits to reside.
        
        """
        # Seed the randomness according to the seed
        random.seed(seed)
        
        # Start generating
        positions = []
        for i in range(bits):
            positions.append(random.randint(0, max_position + i))
        
        # Reset the seed
        random.seed()
        
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

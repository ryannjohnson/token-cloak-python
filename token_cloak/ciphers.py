from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random


class AES256Cipher:
    """Password-centric interface for AES256 encryption.
    
    Source:
        http://stackoverflow.com/a/12525165
    
    """
    
    def __init__(self, key):
        """Init a cipher with a single passphrase.
        
        Args:
            key (bytes): Passphrase for encryption and decryption.
        
        """
        # Set the block size according to AES.
        self.block_size = AES.block_size
        
        # Hash the key to get the right size.
        m = SHA256.new()
        m.update(key)
        self.key = m.digest()


    def encrypt(self, raw):
        """Encrypt bytes using this object's key.
        
        Args:
            raw (bytes): Data to be encrypted.
        
        Returns:
            bytes
        
        """
        # Pad the input so it's the right block size.
        raw = self.pad(raw)
        
        # Create essentially a salt for the encryption.
        iv = Random.new().read( self.block_size )
        
        # Encrypt the new blocks.
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return iv + cipher.encrypt(raw)


    def decrypt(self, raw):
        """Decrypt bytes using this object's key.
        
        Args:
            raw (bytes): Data to be decrypted.
        
        Returns:
            bytes
        
        """
        # Grab the "salt" from the beginning.
        iv = raw[:self.block_size]
        
        # Setup a new cipher and decode/unpad what's there.
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return self.unpad(cipher.decrypt( raw[self.block_size:] ))
    
    
    def pad(self, b):
        """Pad data according to block size."""
        
        # Get the number of bytes to be added for a full block.
        mod = self.block_size - len(b) % self.block_size
        
        # Return the padded bytes.
        return b + mod * chr(mod).encode('ascii')
    
    def unpad(self, b):
        """Unpad data according to the trailing character."""
        
        # Get the last byte.
        last_chr = b[len(b)-1:]
        
        # Grab the number of bytes to shave off.
        to_shave = ord(last_chr.decode('ascii'))
        
        # Return the bytes.
        return b[:-to_shave]
    
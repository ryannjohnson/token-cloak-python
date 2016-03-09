# token-cloak-python

[![Build Status](https://travis-ci.org/ryannjohnson/token-cloak-python.svg?branch=master)](https://travis-ci.org/ryannjohnson/token-cloak-python)
[![PyPI version](https://img.shields.io/pypi/v/token-cloak.svg)](https://pypi.python.org/pypi/token-cloak)

A utility to hide data in public tokens.

## Installation

This package requires Python 3.3 or higher.

To install via `pip`, run the following:

```sh
$ pip install token_cloak
```

## Quick start

Here's an example of how to hide a 64-bit integer inside of a token:

```py
from token_cloak import BitCollection, Token

# Setup the configuration for one kind of token.
token = Token({
    "secret_key": "$3crET-K#y",
    "layers": [{
        "type": "int",
        "bits": 64,
    }],
})

# Generate a base64-encoded token with hidden data.
data = 12345678
public_token = token.encode(data).public_token.to_base64()

# Decode the token.
result = token.decode(public_token, data_type="base64")

# Get the hidden data.
if result:
    print(result.layers[0]) # Equals 12345678
```

## How it works

Let's suppose our original token is 16 bits long.

```py
"0110010110011010"
```

Layer bits are then added to the token in a specific order. In this example, we'll insert `12` as a 4-bit integer at positions 15, 3, 8, and 19. In binary, the decimal `12` is represented as binary `1100`.

```py
"0110010110011010" # Original token

"01100101100110110" # Insert `1` at index 15
                ^
"011100101100110110" # Insert `1` at index 3
    ^
"0111001001100110110" # Insert `0` at index 8
         ^
"01110010011001101100" # Insert `0` at index 19
                    ^
```

Bit positions can be manually set or seeded automatically. If seeded, the seed bits will be inserted into the token after their respective layers (`8` bits by default). The public token is complete when all the layers have been added.

## Configuration

### Secret Key

For any tokens to be encoded or decoded, a `secret_key` is required. It can be set globally or locally:

```py
import token_cloak
from token_cloak import Token

# Set the secret globally.
token_cloak.secret_key = "my global secret key"

# Use the global secret.
global_token = Token({
    "layers": [...],
})

# Set the secret on a per-token basis.
local_token = Token({
    "secret_key": "a local secret ascii key",
    "layers": [...],
})
```

### Layers

Layers contain the instructions for how to create and find the hidden data in public tokens. Every layer requires a `type`. Available data types include `BitCollection`, `bytes`, `int`, and `hex`.

The following example describes a configuration that uses each data type above in the order they are mentioned. 

```py
config = {
    "layers": [
        {
            "type": "BitCollection",
            "bits": 25, # Number of bits in collection
        },
        {
            "type": "bytes",
            "length": 5, # Equals 40 bits (1 byte = 8 bits).
        },
        {
            "type": "int",
            "bits": 5, # Maximum value of 2**5 - 1
            "positions": [8,23,7,3,17], # Manual bit positions
        },
        {
            "type": "hex",
            "length": 5, # Can be even or odd length.
        },
    ],
}
```

##### Layer Keys

Name | Type | Description
--- | --- | ---
`type` | str | Required. Describes the data type to expect during encoding and to return during decoding. Must be in `BitCollection`, `bytes`, `int`, or `hex`.
`bits` | int | Required for `BitCollection` and `int`. Required if no `length` for `bytes` and `hex`. Describes how many bits this data layer uses. If `bits` and `length` are both present, `bits` always takes precedence.
`length` | int | Required if `bits` is not set for `bytes` and `hex` data types. Length allows the user to designate the number of units to use for that data type. For instance, a `bytes` object of `length` 4 would equal 32 `bits`. The `hex` value "3f" (a length of 2) would equal 8 `bits`.
`positions` | list | Optional for any data type. Contains integers denoting the order and position to insert bits into the token. List will be reversed for bit extraction. Must match the number of `bits` for the layer. Must also only contain valid positions 0 <= x <= current_token_length. Note that the token length grows with every insertion, broadening the range of valid positions with every added bit. Order

### Random Bits

The `random_bits` key configures the number of bits to reserve for the original token (512 is the default).

```py
config = {
    "random_bits": 512,
    "layers": [...],
}
```

It is possible to set `random_bits` to 0, in which case no original token will be used.

### Seed bits

The `seed_bits` key determines how many bits are used for seed values for generated bit positions. By default, `seed_bits` is set to 8.

```py
config = {
    "seed_bits": 8,
    "layers": [...],
}
```

Everytime bit positions are automatically generated for a data layer, they use a seed. This seed allows Token Cloak to layer regenerate the same bit positions again from the public token, thereby being able to retrieve the hidden data.

This seed is completely random, but the positions where it's stored in the token are set based on the `secret_key`. Since every bit of the seed is random, it generates no readily-detectable pattern.

_NOTE: The higher the `seed_bits` value is, the difficulty of detecting patterns in the resulting tokens rises._

## Notes on authentication

Currently, when using `Token.decode(public_token)`, the method will only return `None` if an incompatible number of bits is provided. There is no inherent way to determine if a token is authentic.

Authentication can be handled server-side, perhaps by using the original `private_token` as the object of some other means of authentication.

Alternatively, if authentication only serves as a way to prevent unnecessary waste of server resources, consider adding layers to tokens with static or readily-verifiable data.

## Notes on security

While this package offers a way to obfuscate data, there is little to no research about the effectiveness of this method to secure data in any way.

**It is highly recommended not to put any private data in resulting tokens.** This package was originally intended to carry data to improve network infrastructure efficiency and performance, including things such as pointers to services, shard ids, data resources, and other non-confidential data.

## Appendix A

### Token class

The `Token` class encodes and decodes public tokens based on its provided configuration. On init, it takes a single `dict` object to configure it (as seen above).

##### Token.encode(args[,...])

The `encode` method takes a number of positional arguments equal to the number of configured layers. Each argument must be the proper data type and size (in bits) according to its corresponding layer configuration.

Optionally, an additional positional argument may be added as a custom original token (instead of generating one). This argument must be an instance of `BitCollection`, must be the first positional argument, and must have a number of bits equal to the `random_bits` key (512 by default).

This method returns a `TokenResult` object.

##### Token.decode(token[, data_type[, kwargs[,...]]])

The `decode` method requires a token of a data type in `base64` (str), `BitCollection` (BitCollection), `bytes` (bytes), `int` (int), or `hex` (str). 

The `data_type` argument describes how to treat the `token` argument is required for all but an of instance `BitCollection`. Accepted values include `base64`, `bytes`, `int`, and `hex`.

If a `base64` token is url-safe and uses `-_` instead of `+/`, the `url_safe` keyword argument may be set to `True`.

This method returns a `TokenResult` object if successful, and `None` if the input `token` was unable to be decoded.

### BitCollection class

The `BitCollection` class is a standardized way to work with and express binary data within Token Cloak.

##### BitCollection.from_base64(s[, url_safe=False]) _(classmethod)_

Converts a base64-encoded string to a BitCollection. Raises `binascii.Error` if the string is invalid.

The `url_safe` flag can be set to `True` if the input string uses `-_` instead of `+/`.

Returns an instance of BitCollection.

##### BitCollection.from_bytes(b) _(classmethod)_

Converts bytes to a BitCollection. Returns an instance of BitCollection.

##### BitCollection.from_hex(s) _(classmethod)_

Converts a hexadecimal string to a BitCollection. Able to handle strings with an odd number of characters. Returns an instance of BitCollection.

##### BitCollection.from_int(i, bits) _(classmethod)_

Converts an integer to a BitCollection. The `bits` argument determines how many bits will be used to hold the input `int`. The input `int` can have a value no larger than 2**(bits) - 1.

Returns an instance of BitCollection.

##### BitCollection.to_base64([url_safe=False])

Returns a base64-encoded string of the bits in BitCollection. If `url_safe` is `True`, then `-_` will be used in place of `+/`.

##### BitCollection.to_bytes()

Returns bytes of the bits in BitCollection. Will be right-padded with `0` bits if not divisible by 8.

##### BitCollection.to_hex()

Returns bytes of the bits in BitCollection. Will be right-padded with `0` bits if not divisible by 4.

##### BitCollection.to_int()

Returns int representation of the bits in BitCollection.

### TokenResult class

This class holds the results from a `Token` encoding or decoding. It always holds the same 3 attributes:

##### TokenResult.public_token

This attribute is a `BitCollection` containing the encoded token.

##### TokenResult.private_token

This attribute is a `BitCollection` containing the original token.

##### TokenResult.layers

This attribute is a `list` containing data according to the `layers` key in the configuration `dict` given to the `Token` class at instantiation. The data is in the same order and data type as in the configuration.
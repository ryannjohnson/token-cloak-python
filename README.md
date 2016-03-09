# token-cloak-python

[![Build Status](https://travis-ci.org/ryannjohnson/token-cloak-python.svg?branch=master)](https://travis-ci.org/ryannjohnson/token-cloak-python)

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
from token_cloak import Token

# Setup the configuration for one kind of token.
token = Token({
    "secret_key": "$3crET-K#y",
    "layers": [
        {
            "type": "int",
            "bits": 64,
        },
    ],
})

# Generate a base64-encoded token with hidden data.
hidden = 12345678
public_token = token.encode(hidden).public_token.to_base64()

# Decode the token.
result = token.decode(public_token, data_type="base64")

# Get the hidden data.
result.layers[0] # Equals 12345678
```

## How it works

The first step is to start with a random series of bits. In this example, the token is 16 bits long.

```py
0110010110011010
```

Next, layers are added in the order they are set. In this example, we'll add `12` as a 4-bit integer at positions 15, 3, 8, and 19, in that order. In binary, the decimal `12` is represented as binary `1100`.

```py
0110010110011010 # Original token

01100101100110110 # Add `1` at index 15
               ^
011100101100110110 # Add `1` at index 3
   ^
0111001001100110110 # Add `0` at index 8
        ^
01110010011001101100 # Add `0` at index 19
                   ^
```

## Advanced usage

The following are a few common use cases for Token Cloak.

### Random token + user id

In web
# token-cloak-python

[![Build Status](https://travis-ci.org/ryannjohnson/token-cloak-python.svg?branch=master)](https://travis-ci.org/ryannjohnson/token-cloak-python)

A utility to hide secret data in public tokens.

## Installation

This package requires Python 3.3 or higher.

To install via `pip`, run the following:

```sh
$ pip install token_cloak
```

## Quick Start

Here is a simple example of how to use Token Cloak.

```py
from token_cloak import Token

# Setup the configuration for one kind of token.
token = Token({
    "secret_key": "$3crET-K#y", # Seeds randomness.
    "layers": [
        {
            "type": "int", # Integer data type
            "bits": 64, # 64-bit integer
        },
    ],
})

# Generate a base64 token with hidden data.
hidden = 12345678
public_token = token.encode(hidden).public_token.to_base64()

# Decode the token.
result = token.decode(public_token, data_type='base64')
assert hidden == result.layers[0]
```
"""
Token Cloak is a utility for lacing public tokens with data.
"""

__license__ = 'MIT License'
__version__ = '0.1.0'


secret_key = None
"""Controls pseudo-randomness within Token Cloak."""

# Token
from .tokens import Token

# BitCollection
from .collections import BitCollection
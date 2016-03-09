"""
Token Cloak is a utility for hiding data in public tokens.
"""

__license__ = 'MIT License'
__version__ = '0.1.1'


secret_key = None
"""Controls pseudo-randomness within Token Cloak."""

# Token
from .tokens import Token

# BitCollection
from .collections import BitCollection
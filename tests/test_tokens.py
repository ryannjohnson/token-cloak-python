from token_cloak import Token


class TestToken:
    
    def test_int_token(self):
        token = Token({
            "secret_key": "music makes me lose control",
            "random_bits": 32,
            "seed_bits": 4,
            "layers": [
                {
                    "type": "int",
                    "bits": 8,
                }
            ],
        })
        first = token.encode(5)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
        
        
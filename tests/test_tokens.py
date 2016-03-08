from token_cloak import Token


class TestToken:
    
    @classmethod
    def setup_class(cls):
        cls.config = {
            "secret_key": "music makes me lose control",
            "random_bits": 32,
            "seed_bits": 4,
            "layers": [
                {
                    "type": "int",
                    "bits": 8,
                }
            ],
        }
    
    @classmethod
    def teardown_class(cls):
        cls.config = {}
    
    def test_int_token(self):
        token = Token(self.config)
        first = token.encode(5)
        second = token.decode(first.public_token)
        print(first.private_token.to_hex(), second.private_token.to_hex())
        assert first.private_token.to_int() == second.private_token.to_int()
        print(second.layers)
        assert False
        
    
from token_cloak import Token


class TestToken:
    
    @classmethod
    def setup_class(cls):
        cls.config = {
            "secret_key": "music makes me lose control",
            "random_bits": 32,
            "seed_bits": 4,
        }
    
    @classmethod
    def teardown_class(cls):
        cls.config = {}
    
    def test_int_token(self):
        self.config["layers"] = [
            {
                "type": "int",
                "bits": 8,
            }
        ]
        token = Token(self.config)
        first = token.encode(5)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
        assert second.layers[0] == 5
        
    
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
    
    def test_int_layer(self):
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
    
    def test_bytes_layer(self):
        self.config["layers"] = [
            {
                "type": "bytes",
                "length": 8,
            }
        ]
        token = Token(self.config)
        bytes_ = "turtles!".encode('ascii')
        first = token.encode(bytes_)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
        assert second.layers[0] == bytes_
    
    def test_hex_layer(self):
        self.config["layers"] = [
            {
                "type": "hex",
                "length": 8,
            }
        ]
        token = Token(self.config)
        s = "af932875"
        first = token.encode(s)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
        assert second.layers[0] == s
        
    
from token_cloak import BitCollection, Token


class TestToken:
    
    def setup_method(cls, method):
        cls.config = {
            "secret_key": "music makes me lose control",
            "random_bits": 32,
            "seed_bits": 4,
        }
    
    def teardown_method(cls, method):
        cls.config = {}
    
    def test_no_token(self):
        del self.config["random_bits"]
        self.config["layers"] = [
            {
                "type": "int",
                "bits": 8,
            }
        ]
        token = Token(self.config)
        first = token.encode(7)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
        assert 7 == second.layers[0]
    
    def test_custom_token(self):
        i = 634543
        b = BitCollection.from_int(i, bits=32)
        token = Token(self.config)
        first = token.encode(b)
        second = token.decode(first.public_token)
        assert i == second.private_token.to_int()
    
    def test_bitcollection_layer(self):
        self.config["layers"] = [
            {
                "type": "BitCollection",
                "bits": 8,
            }
        ]
        token = Token(self.config)
        b = BitCollection.from_int(7, bits=8)
        first = token.encode(b)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
    
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
    
    def test_bytes_layer_bits(self):
        self.config["layers"] = [
            {
                "type": "bytes",
                "bits": 64,
            }
        ]
        token = Token(self.config)
        bytes_ = "turtles!".encode('ascii')
        first = token.encode(bytes_)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
        assert second.layers[0] == bytes_
    
    def test_bytes_layer_length(self):
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
    
    def test_hex_layer_bits(self):
        self.config["layers"] = [
            {
                "type": "hex",
                "bits": 32,
            }
        ]
        token = Token(self.config)
        s = "af932875"
        first = token.encode(s)
        second = token.decode(first.public_token)
        assert first.private_token.to_int() == second.private_token.to_int()
        assert second.layers[0] == s
    
    def test_hex_layer_length(self):
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
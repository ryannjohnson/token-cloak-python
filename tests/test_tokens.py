import random
from token_cloak import BitCollection, Token


class TestToken:
    
    def setup_method(self, method):
        self.config = {
            "secret_key": "music makes me lose control",
            "random_bits": 123,
            "seed_bits": 4,
        }
        self.start = 23
        self.end = 47
    
    def teardown_method(self, method):
        pass
    
    @staticmethod
    def randint(i):
        return random.randint(0, 2 ** (i - 1))
    
    def test_no_token(self):
        del self.config["random_bits"]
        for i in range(self.start, self.end):
            self.config["layers"] = [
                {
                    "type": "int",
                    "bits": i,
                }
            ]
            a = self.randint(i)
            token = Token(self.config)
            first = token.encode(a)
            second = token.decode(first.public_token)
            assert first.private_token.to_int() == second.private_token.to_int()
            assert a == second.layers[0]
    
    def test_custom_token(self):
        for i in range(self.start, self.end):
            self.config["random_bits"] = i
            a = self.randint(i)
            b = BitCollection.from_int(a, bits=i)
            token = Token(self.config)
            first = token.encode(b)
            second = token.decode(first.public_token)
            assert a == second.private_token.to_int()
    
    def test_base64_token(self):
        for i in range(self.start, self.end):
            self.config["random_bits"] = i
            token = Token(self.config)
            first = token.encode()
            second = token.decode(
                    first.public_token.to_base64().rstrip('='),
                    data_type='base64')
            assert second.private_token.to_int() == first.private_token.to_int()
    
    def test_bitcollection_layer(self):
        for i in range(self.start, self.end):
            self.config["layers"] = [
                {
                    "type": "BitCollection",
                    "bits": i,
                },
            ]
            token = Token(self.config)
            b = BitCollection.from_int(self.randint(i), bits=i)
            first = token.encode(b)
            second = token.decode(first.public_token)
            assert first.private_token.to_int() == second.private_token.to_int()
    
    def test_int_layer(self):
        for i in range(self.start, self.end):
            self.config["layers"] = [
                {
                    "type": "int",
                    "bits": i,
                },
            ]
            a = self.randint(i)
            token = Token(self.config)
            first = token.encode(a)
            second = token.decode(first.public_token.to_int(), data_type='int')
            assert first.private_token.to_int() == second.private_token.to_int()
            assert second.layers[0] == a
            assert second.public_token.length() == self.config["random_bits"] + i+4
    
    def test_bytes_layer_bits(self):
        for i in range(self.start, self.end):
            self.config["layers"] = [
                {
                    "type": "bytes",
                    "bits": i * 8,
                },
            ]
            bytes_ = bytes()
            for j in range(i):
                bytes_ += bytes([random.randint(0, 2 ** (8 - 1))])
            print(i, bytes_)
            token = Token(self.config)
            first = token.encode(bytes_)
            second = token.decode(first.public_token.to_bytes(), data_type='bytes')
            assert first.private_token.to_int() == second.private_token.to_int()
            assert second.layers[0] == bytes_
    
    def test_bytes_layer_length(self):
        for i in range(self.start, self.end):
            self.config["layers"] = [
                {
                    "type": "bytes",
                    "length": i,
                },
            ]
            token = Token(self.config)
            bytes_ = bytes()
            for j in range(i):
                bytes_ += bytes([random.randint(0, 2 ** (8 - 1))])
            a = BitCollection.from_bytes(bytes_)
            first = token.encode(bytes_)
            second = token.decode(first.public_token.to_bytes(), data_type='bytes')
            assert first.private_token.to_int() == second.private_token.to_int()
            assert second.layers[0] == bytes_
    
    def test_hex_layer_bits(self):
        for i in range(self.start, self.end):
            self.config["layers"] = [
                {
                    "type": "hex",
                    "bits": i * 4,
                },
            ]
            token = Token(self.config)
            s = ""
            for j in range(i):
                s += "0123456789abcdef"[random.randint(0,15)]
            first = token.encode(s)
            second = token.decode(first.public_token)
            assert first.private_token.to_int() == second.private_token.to_int()
            assert second.layers[0] == s
    
    def test_hex_layer_length(self):
        for i in range(self.start, self.end):
            self.config["layers"] = [
                {
                    "type": "hex",
                    "length": i,
                },
            ]
            token = Token(self.config)
            s = ""
            for j in range(i):
                s += "0123456789abcdef"[random.randint(0,15)]
            first = token.encode(s)
            second = token.decode(first.public_token)
            assert first.private_token.to_int() == second.private_token.to_int()
            assert second.layers[0] == s
    
    def test_int_layer_positions(self):
        for i in range(self.start, self.end):
            positions = []
            for j in range(i):
                positions.append(random.randint(0, i + j))
            self.config["layers"] = [
                {
                    "type": "int",
                    "bits": i,
                    "positions": positions,
                },
            ]
            a = self.randint(i)
            token = Token(self.config)
            first = token.encode(a)
            second = token.decode(first.public_token)
            assert first.private_token.to_int() == second.private_token.to_int()
            assert second.layers[0] == a
            assert second.public_token.length() == self.config["random_bits"] + i
    
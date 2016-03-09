from token_cloak import BitCollection

class TestBitCollection:
    
    def test_base64(self):
        msg = 'bW9vc2U=='
        b = BitCollection.from_base64(msg)
        s = b.to_base64()
        assert msg == s
    
    def test_hex(self):
        msg = '1234567890abcdef'
        b = BitCollection.from_hex(msg)
        s = b.to_hex()
        assert msg == s
        
    def test_int(self):
        msg = 12345
        b = BitCollection.from_int(msg, bits=50)
        s = b.to_int()
        assert msg == s
    
    def test_bytes(self):
        msg = 'moose'.encode('utf8')
        b = BitCollection.from_bytes(msg)
        s = b.to_bytes()
        assert msg == s
    
from token_cloak import BitCollection

class TestBitCollection:
    
    def test_from_base64(self):
        msg = 'bW9vc2U=='
        b = BitCollection.from_base64(msg)
        s = b.to_base64()
        assert s == msg
    

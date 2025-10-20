from models import Format
from models.encoder import Encoder

class TestFormat:

    f1 = Format('name', 'enc', 'name enc', None)
    f2 = Format('name', 'enc', None, Encoder('lame', '.whacc', 'some str'))
    f3 = Format('some other name', 'some other enc', None, None)

    def test_equality(self):
        assert self.f1 == self.f2
        assert self.f1 != self.f3
        assert self.f2 != self.f3

    def test_set(self):
        s1 = set([self.f1, self.f2])
        assert len(s1) == 1
        # the __hash__es should be the same!

        assert self.f1 in s1
        assert self.f2 in s1
        assert self.f3 not in s1
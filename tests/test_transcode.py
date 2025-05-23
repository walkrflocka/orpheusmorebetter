import transcode

class TestExtMatcher:
    def test_single(self):
        func = transcode.ext_matcher('.flac')
        assert func('folder/something.flac')
        assert func('someotherthing.flac')
        assert not func('folder/file.mp3')
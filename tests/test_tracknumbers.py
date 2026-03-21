import services.tagging as tagging

class TrackNumTester:
    def test_single(self):
        assert tagging.format_track_and_disc_numbers("1","2") == "1/2"
        assert tagging.format_track_and_disc_numbers("10/2","2") == "10/2"
        assert tagging.format_track_and_disc_numbers("A1/3","4") == "A1/4"
        assert tagging.format_track_and_disc_numbers("A1","2") == "A1/2"
        assert tagging.format_track_and_disc_numbers("1/2","") == "1/2"

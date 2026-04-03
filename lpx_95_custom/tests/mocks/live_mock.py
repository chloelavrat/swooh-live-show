"""
Stubs for Live.Song, Live.Clip, Live.DrumChain — allow tests to run outside Ableton.
"""


class MockNote:
    """Represents (pitch, time, duration, velocity, muted) as a tuple-like."""
    def __init__(self, pitch=36, time=0.0, duration=0.25, velocity=100, muted=False):
        self._data = (pitch, time, duration, velocity, muted)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, idx):
        return self._data[idx]


class MockClip:
    def __init__(self, loop_end=4.0):
        self.loop_end  = loop_end
        self.is_playing = False
        self._notes: list = []
        self._notes_listeners = []

    def add_notes_listener(self, fn):
        self._notes_listeners.append(fn)

    def remove_notes_listener(self, fn):
        if fn in self._notes_listeners:
            self._notes_listeners.remove(fn)

    def get_notes(self, from_time, from_pitch, time_span, pitch_span):
        result = []
        for note in self._notes:
            pitch, time, duration, velocity, muted = note
            if (from_time <= time < from_time + time_span and
                    from_pitch <= pitch < from_pitch + pitch_span):
                result.append(tuple(note))
        return tuple(result)

    def set_notes(self, notes):
        for note in notes:
            self._notes.append(list(note))
        for fn in self._notes_listeners:
            fn()

    def remove_notes(self, from_time, from_pitch, time_span, pitch_span):
        self._notes = [
            n for n in self._notes
            if not (from_time <= n[1] < from_time + time_span and
                    from_pitch <= n[0] < from_pitch + pitch_span)
        ]
        for fn in self._notes_listeners:
            fn()


class MockDrumChain:
    def __init__(self, name="Chain", note=36, color=5, mute=False):
        self.name  = name
        self.note  = note
        self.color = color
        self.mute  = mute
        self.solo  = False


class MockDevice:
    def __init__(self, chains=None):
        self.chains = chains or [
            MockDrumChain("Kick",   36, 5,  False),
            MockDrumChain("Snare",  38, 21, False),
            MockDrumChain("HiHat",  42, 9,  False),
            MockDrumChain("Clap",   39, 48, False),
        ]


class MockClipSlot:
    def __init__(self, clip=None):
        self.clip = clip


class MockTrack:
    def __init__(self, device=None, clips=None):
        device = device or MockDevice()
        self.devices    = [device]
        self.clip_slots = clips or [MockClipSlot(MockClip()), MockClipSlot(None)]


class MockView:
    def __init__(self, track=None):
        self.selected_track = track or MockTrack()


class MockSong:
    def __init__(self):
        self.tempo              = 120.0
        self.is_playing         = False
        self.current_song_time  = 0.0
        self._song_time_listeners = []
        self.view               = MockView()

    def add_current_song_time_listener(self, fn):
        self._song_time_listeners.append(fn)

    def remove_current_song_time_listener(self, fn):
        if fn in self._song_time_listeners:
            self._song_time_listeners.remove(fn)

    def advance_time(self, beats: float):
        """Test helper: move playhead forward and fire listeners."""
        self.current_song_time += beats
        for fn in self._song_time_listeners:
            fn()

from abc import ABC, abstractmethod
from protocol.midi import MidiMessage


class BaseBehavior(ABC):

    def __init__(self, adapter, song):
        self.adapter = adapter   # DeviceAdapter instance
        self.song    = song      # Live.Song.Song (or mock)

    @abstractmethod
    def on_enter(self):
        """Called when this mode becomes active. Draw initial LED state."""
        ...

    @abstractmethod
    def on_exit(self):
        """Called when this mode is deactivated. Clear relevant LEDs."""
        ...

    @abstractmethod
    def handle_midi(self, msg: MidiMessage) -> bool:
        """
        Process an incoming MIDI message.
        Return True if consumed, False to pass through to lower behaviors.
        """
        ...

    def tick(self):
        """Called on each scheduler tick (if registered with the router). Optional."""
        pass

    def snapshot(self) -> dict:
        """Return serializable state for the bridge StateWriter. Override in subclasses."""
        return {}

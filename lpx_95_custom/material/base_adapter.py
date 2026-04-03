from abc import ABC, abstractmethod
from .zone import Zone


class DeviceAdapter(ABC):

    @abstractmethod
    def zone(self, name: str) -> Zone:
        """Return a Zone object by name."""
        ...

    @abstractmethod
    def set_pad_rgb(self, pad: int, r: int, g: int, b: int):
        """Set a single pad to an RGB color."""
        ...

    @abstractmethod
    def set_pad_palette(self, pad: int, color_index: int):
        """Set a single pad to a Novation palette index."""
        ...

    @abstractmethod
    def set_pad_pulse(self, pad: int, color_index: int):
        """Set a single pad to a pulsing (breathing) Novation palette color."""
        ...

    @abstractmethod
    def set_pad_flash(self, pad: int, color_a: int, color_b: int):
        """Set a single pad to flash between two Novation palette colors."""
        ...

    @abstractmethod
    def clear_pad(self, pad: int):
        """Turn off a single pad."""
        ...

    @abstractmethod
    def clear_all(self):
        """Turn off all pads."""
        ...

    @abstractmethod
    def enter_programmer_mode(self):
        """Switch the device to Programmer mode for full pad control."""
        ...

    @abstractmethod
    def exit_programmer_mode(self):
        """Return the device to Live/normal mode."""
        ...

    def send_note_on(self, note: int, velocity: int):
        """Send a MIDI Note On to the device output (for trigger roll, etc.)."""
        pass

    def send_note_off(self, note: int):
        """Send a MIDI Note Off to the device output."""
        pass

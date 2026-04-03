from dataclasses import dataclass
from .constants import (
    STATUS_NOTE_ON, STATUS_NOTE_OFF, STATUS_CC,
    STATUS_SYSEX_START, TYPE_MASK, CHANNEL_MASK,
)


@dataclass
class MidiMessage:
    status: int   # raw status byte
    data1: int
    data2: int

    @property
    def channel(self) -> int:
        return self.status & CHANNEL_MASK

    @property
    def msg_type(self) -> int:
        return self.status & TYPE_MASK

    @property
    def is_note_on(self) -> bool:
        return self.msg_type == STATUS_NOTE_ON and self.data2 > 0

    @property
    def is_note_off(self) -> bool:
        return self.msg_type == STATUS_NOTE_OFF or (
            self.msg_type == STATUS_NOTE_ON and self.data2 == 0
        )

    @property
    def is_cc(self) -> bool:
        return self.msg_type == STATUS_CC

    @property
    def is_sysex(self) -> bool:
        return self.status == STATUS_SYSEX_START

    @property
    def note(self) -> int:
        """Alias for data1 when message is a note event."""
        return self.data1

    @property
    def velocity(self) -> int:
        """Alias for data2 when message is a note event."""
        return self.data2

    @property
    def cc_number(self) -> int:
        """Alias for data1 when message is a CC event."""
        return self.data1

    @property
    def cc_value(self) -> int:
        """Alias for data2 when message is a CC event."""
        return self.data2


def parse(status: int, data1: int, data2: int) -> MidiMessage:
    return MidiMessage(status=status, data1=data1, data2=data2)

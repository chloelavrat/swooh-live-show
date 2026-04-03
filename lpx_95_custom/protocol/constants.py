NOVATION_SYSEX_HEADER = (0x00, 0x20, 0x29, 0x02, 0x0C)

# Programmer mode on/off
PROGRAMMER_MODE_ON  = NOVATION_SYSEX_HEADER + (0x0E, 0x01)
PROGRAMMER_MODE_OFF = NOVATION_SYSEX_HEADER + (0x0E, 0x00)

# Pad note layout: bottom-left = 11, row-major, 9-wide grid
PAD_OFFSET  = 11
GRID_WIDTH  = 9
GRID_HEIGHT = 9
ROW_STRIDE  = 10  # note increment per row

# CC numbers (channel 1 in hardware = channel index 0 in code)
CC_OCTAVE_UP   = 89
CC_OCTAVE_DOWN = 79
CC_NAV_UP      = 91
CC_NAV_DOWN    = 92
CC_NAV_LEFT    = 93
CC_NAV_RIGHT   = 94

# Special pad note numbers
PAD_MUTE_BUTTON      = 89
PAD_TRIGGER_ROLL     = 79
PAD_LOCK_TOGGLE      = 19
PAD_COLOR_CHANGE     = 9
PAD_MUTE_MODE_CHANGE = 69   # control strip row 5 — toggles mute momentary/latch

# MIDI status byte masks
STATUS_NOTE_OFF    = 0x80
STATUS_NOTE_ON     = 0x90
STATUS_CC          = 0xB0
STATUS_SYSEX_START = 0xF0
STATUS_SYSEX_END   = 0xF7
CHANNEL_MASK       = 0x0F
TYPE_MASK          = 0xF0

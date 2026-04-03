from dataclasses import dataclass, field


@dataclass
class Zone:
    name: str
    role: str       # e.g. "drum_selector", "step_grid", "clip_navigation"
    pads: list      # ordered list of pad note numbers, row-major (bottom-left origin)
    width: int      # columns
    height: int     # rows

    def pad_at(self, row: int, col: int) -> int:
        """Return pad note number at (row, col). row 0 = bottom."""
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            raise IndexError(
                "({}, {}) out of zone '{}' bounds ({}x{})".format(
                    row, col, self.name, self.width, self.height
                )
            )
        return self.pads[row * self.width + col]

    def index_of(self, pad: int):
        """Return (row, col) for a pad note number. row 0 = bottom."""
        try:
            idx = self.pads.index(pad)
        except ValueError:
            raise ValueError("Pad {} not in zone '{}'".format(pad, self.name))
        return (idx // self.width, idx % self.width)

    def contains(self, pad: int) -> bool:
        return pad in self.pads

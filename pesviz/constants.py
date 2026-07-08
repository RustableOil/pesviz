"""Search-phase codes/colors/labels, coloring helpers, and animation timing constants."""

PHASE_VOID = 1
PHASE_INIT = 2
PHASE_PERP = 3
PHASE_EIGN = 4
PHASE_LANC = 5
PHASE_RELX = 6
PHASE_OVER = 7
PHASE_SMTH = 8
PHASE_RSET = 9

PHASE_COLORS = {
    PHASE_VOID: (0.55, 0.55, 0.55, 1.0),
    PHASE_INIT: (0.25, 0.60, 0.95, 1.0),
    PHASE_PERP: (0.20, 0.85, 0.75, 1.0),
    PHASE_EIGN: (0.95, 0.70, 0.10, 1.0),
    PHASE_LANC: (0.75, 0.30, 0.95, 1.0),
    PHASE_RELX: (0.25, 0.85, 0.40, 1.0),
    PHASE_OVER: (0.95, 0.45, 0.10, 1.0),
    PHASE_SMTH: (0.40, 0.75, 0.95, 1.0),
    PHASE_RSET: (0.90, 0.20, 0.25, 1.0),
}

HOVER_COLOR = (1.00, 1.00, 1.00, 1.0)
FORCE_COLOR = (0.00, 0.00, 1.00, 1.0)
EIGEN_COLOR = (0.00, 1.00, 0.00, 1.0)

HEATMAP_LOW_COLOR = (0.10, 0.20, 0.90, 1.0)
HEATMAP_HIGH_COLOR = (0.95, 0.15, 0.10, 1.0)

def heatmap_color(t):
    """Linearly interpolate from HEATMAP_LOW_COLOR to HEATMAP_HIGH_COLOR for t in [0, 1]."""
    t = min(max(t, 0.0), 1.0)
    return tuple(lo + (hi - lo) * t for lo, hi in zip(HEATMAP_LOW_COLOR, HEATMAP_HIGH_COLOR))

PHASE_LABELS = {
    PHASE_VOID: "VOID - nothing",
    PHASE_INIT: "INIT - initial push",
    PHASE_PERP: "PERP - perpendicular relaxation",
    PHASE_EIGN: "EIGN - push with eigenvector",
    PHASE_LANC: "LANC - lanczos",
    PHASE_RELX: "RELX - relaxation",
    PHASE_OVER: "OVER - push over saddle point",
    PHASE_SMTH: "SMTH - smoothing steps",
    PHASE_RSET: "RSET - reset",
}

ANIMATION_TICK_THR = 0.2 # in seconds
FF_ANIMATION_TICK_THR = 0.05 # in seconds
END_PAUSE_DURATION = 5.0 # in seconds; pause once animation reaches the last step before it loops

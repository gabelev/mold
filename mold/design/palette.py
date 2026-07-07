"""The fixed petri palette — the constant of Mold's visual identity.

Per the design spec: the palette *family* is FIXED (substrate green-black,
agar, viridian, sulphur, bruise, spore); per-issue drift moves temperature and
dominant accent WITHIN this gamut but never leaves the biological family.
"""

PALETTE = {
    "substrate": "#0a0f0c",   # green-black ground
    "agar": "#e8e4d8",        # pale growth-medium field
    "viridian": "#1f7a6d",    # the mold itself
    "chartreuse": "#9acd32",  # bloom
    "sulphur": "#d4c53a",     # fruiting accent
    "bruise": "#8b2f6b",      # one magenta bruise where it's spreading
    "spore": "#4a5548",       # dusty midtone
}

# Per-issue drift bounds (the gamut walls). The Art Director may move accent
# dominance and temperature inside these; leaving the family is FORBIDDEN.
GAMUT = {
    "accents": ("viridian", "chartreuse", "sulphur", "bruise"),
    "max_bruise_ratio": 0.15,  # the bruise is a wound, not a theme
}

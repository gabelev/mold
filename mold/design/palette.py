"""The MOLD palette — BOLD and electric, harmonized with the home page.

Deliberately loud: a near-black gallery ground, off-white body for long-form
readability, and four electric accents (yellow, pink, klein blue, acid green)
that carry all the shout. This replaces the earlier muted "petri" palette —
issues now match the home page's energy, not a mood-board of moss.

The key names are legacy handles (kept so the kit/shell don't churn); read them
by their comment, not their botanical past.
"""

PALETTE = {
    "substrate": "#0d0d0d",   # near-black — the page ground
    "agar": "#f4f1e8",        # bone — body text on dark; black text on light blocks
    "viridian": "#2418ff",    # KLEIN BLUE (accent)
    "chartreuse": "#7cff00",  # ACID GREEN (accent)
    "sulphur": "#ebff00",     # ELECTRIC YELLOW (accent / the iconic shout)
    "bruise": "#ff1fb4",      # HOT PINK (accent)
    "orange": "#ff6a00",      # ORANGE (accent / color block)
    "spore": "#8a8f98",       # neutral gray — labels, rules, folios
}

# Per-issue the Art Director picks ONE accent to dominate. All four are loud;
# there is no "stay muted" gamut anymore — the only rule is high contrast.
GAMUT = {
    "accents": ("sulphur", "bruise", "viridian", "chartreuse"),  # yellow, pink, blue, acid
    "max_bruise_ratio": 0.5,  # hot pink can run hot now; it's a feature
}

# Deck Tool 1.8.0

Glass is a separate effect option. Clear Case and Crystal remain available with the new native transparency materials. Choose display glass, animated water, frosted/glossy plastic with embedded artwork or PCB, and irregular cut crystal. Tune tint, haze, reflections and refraction in the tool. Artwork retains an exposed transparent border.

Layered Artwork Springs supports a background, moving artwork and foreground. Existing spring and attachment controls remain available.

This release fixes an export partitioning fault that removed newly authored decks from the in-game inventory. Deck collections and per-deck material registrations now remain in content exports. A regression check verifies that authored items are referenced by an exported inventory collection. Re-export projects affected by missing inventory entries.

## Requirements

Install SDEC 3.3.0 separately, with one copy enabled first in the mod list. The tool and its deck exports do not bundle SDEC. The bottom-of-window SDEC link remains available. ZIP/direct exports require a separately installed Studio compiler supporting shared-core board-loader inheritance. Transparency uses the official ReSkate runtime.

## Validation

The four transparency finishes were visually checked on the official runtime. The export correction passes the runtime partition tests, and all 32 decks in the complete test pack have verified native inventory references. The corrected pack has not yet received a fresh in-game visual confirmation. Preview lighting and geometry remain approximate.

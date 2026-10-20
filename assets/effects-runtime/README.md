# Runtime-only resources

These six resources belong to the shared core, not deck content. They load and
retain the empty compositor background through the donor bundle lookup and
suppress the Primitive additive foil pass only for a recognised Deck Tool atlas.
The four-colour atlas signature and ABI 1 remain unchanged.

The runtime deliberately omits the high-resolution compositor texture-set and
prefab overrides: the user confirmed those caused persistent blur on the supplied
Animated Skulls Croptop. The seven shader resources remain enabled.

The manifest records encoded FBMOD payload hashes and native loading descriptors.
The builder checks hashes and reindexes descriptors when adding these resources.
Keep the donor bundle lookup in content too: its per-deck rows are additive.

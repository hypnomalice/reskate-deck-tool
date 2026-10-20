# Shared effects runtime (experimental)

The runtime owns six effect programs, the empty native graphic texture, the
scoped sticker-compositor Lua, and the compositor resolution settings. Content
packs retain artwork, masks, thumbnails, items, private material recipes and
their additive shader lookup rows. Content packs must not carry a renderer.

`effects_runtime.split_pack` validates and normalizes a supported legacy export
before partitioning it. `migrate_file` creates separate files and an ABI contract,
preserving the original. Neither API modifies installed mods or load order.

ABI 1 preserves the released atlas layout, effect markers, material parameters
and private material identities. Runtime updates must retain those decoding
paths. Adding a new effect must not require changing existing content. Changes
to this contract require a new ABI with explicit handling for older content.

Current status: resource partitioning and native compilation pass. The user reports
Ghost Rare, smooth depth, classic effects, Bridget and scrolling animations, stickers
and board break working with the supplied crop top, including reversed load order.
Disabling only the runtime breaks the converted decks while the crop top continues.
This establishes the expected dependency and compatibility with that specific mod.
The Qt app now exports runtime-based content by default; the lower-level engine
retains its standalone default for existing automation. Runtime setup and one-time
migration replace the repeated compatibility repair menu in this candidate.

## Compatibility limits

This first candidate still uses the six existing shared program identities.
Central ownership fixes duplication between migrated Deck Tool packs; it does
not establish isolation from unrelated shader mods. The crop-top package supplied
by the user is the external compatibility fixture. Its full bundle catalogue
must not be mistaken for a list of changed shaders.

An installation manager must identify legacy embedded renderers and explain or
resolve their priority. A sidecar contract is not an enforced launcher dependency.
Runtime setup saves an importable runtime FBMOD; exporting content also saves it
beside the content with a dependency contract. Automatic launcher installation and
missing-runtime enforcement are not implemented. Users import the runtime once
through Studio, then update that one installed mod when effects change.
Do not publish this candidate as an automatic universal conflict resolver.

# Deck Tool 1.11.0

Parallax layers can now have independent donor Pearl holographic finishes. A normal foreground can remain unchanged over a foil background, and a middle layer can have its own finish, strength and PNG mask.

- Add Normal / Holographic, 0–100% strength, and Light artwork / Whole layer / Mask PNG controls per layer.
- Preserve settings, relative mask paths and artwork placement through save, reload and normal export.
- Apply foil before layer compositing so normal layers keep their colours and transparency.
- Preserve the shader recognition strip and validate its filtered sample before exporting. This prevents the bare-wood fallback found in the initial beta.
- Retain existing deck effects and projects. The previous whole-board overlay remains supported.

Use SDEC 3.6.0 or newer for the new finish. Authors keep the existing Studio compiler setup; no new compiler requirement or additional plugin was added. Recipients need ReSkate, SDEC and the deck pack.

The background, foreground, PNG-mask and three-layer tests were confirmed working in ReSkate Dev. All 249 authoring checks were covered, including targeted reruns after repairing stale test fixtures and enabling Luau parity testing. Actual compiled atlas data and the merged material’s 23 referenced shader containers were verified. Twelve native vertex/layout pipeline cases passed. These checks do not establish multiplayer, cross-platform rendering or GPU performance across systems. Preview lighting remains approximate.

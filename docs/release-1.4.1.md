# ReSkate Deck Tool 1.4.1

Fixes preview artwork placement and adds a 2D / 3D preview switch.

- The preview uses the standard donor deck's measured artwork UV coverage. Previously the complete effect image was stretched over the visible board, making its position differ from the exported deck. The export renderer already accounts for the reserved shader strip; no second strip offset is added.
- Animation, effect preview and live image placement all pass through the same preview-only mapping.
- Both 2D and 3D show that mapped artwork. Drag in 3D to orbit and double-click to reset. The enlarged preview follows the selected view.
- The 3D shape is a procedural standard-deck approximation, with nose/tail kicks and concave rails. It is not game geometry or a game-lighting preview. Other custom board shapes may use different UVs.
- Existing projects, image positions, exports, shader payloads and core requirements are unchanged.

This standalone release does **not** include the new experimental SDEC physics, reactive, tracking or glass effects. It requires no custom ReSkate DLL. Keep using the matching existing SDEC core.

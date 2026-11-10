# Deck Tool 1.6.6 - synchronized e-ink and layered clear cases

Requires **SDEC 2.1.5**, enabled at **number 1** in the mod list. Keep one core enabled.

- E-ink retains the accepted reference flash and switches the fixed page at full flash in either tilt direction. Refresh tilt range controls angular width. No timed controller or custom ReSkate DLL is required.
- Clear Case places artwork inside a layered shell, with frosted/glossy finishes, working tint, blur and depth controls. Default internal blur is 42%.
- Separate full-canvas masks place decorative case screws and moulded details on the underside. White screw-mask spots create up to 16 screw bosses; white/grey detail-mask areas add plastic detail. Black removes the defaults. Reset restores them. The upper/grip side keeps fixed truck holes. Grip tape defaults off.
- Repairs native material registration for clear-case and glitch exports, preserving their material routes when combined with SDEC.
- Preserves RGB, single-colour and two-colour glitch options, optional white sheen, and opt-in holographic depth/parallax.

Use a shader-capable Studio compiler supporting core board-loader inheritance for direct Clear Case/Glitch exports. Set your game folder and compiler in File > Export setup. The compiler and SDEC are installed separately.

Re-export existing projects to use the updated effects. The shared core also preserves the original unmarked e-ink reference behavior. Development effects remain in progress.

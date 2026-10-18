import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

GUIDES = {
    'Animated GIF': '''ANIMATED GRAPHICS

Select Animated GIF from Effect, then choose a GIF, animated PNG or animated WebP.
The clip loops on the underside without a lenticular effect. It starts centred,
preserves its proportions, and does not upscale small sources. Adjust placement
changes its size and position with a playing preview. Background colour fills
transparent areas and the rest of the deck.

This beta supports 1–128 frames and loops up to 40.95 seconds. Frame timings are
rounded to 10 milliseconds. Storage resolution is reduced when needed to fit
the game texture, so shorter clips can retain more detail. The preview cannot
reproduce texture compression or game lighting exactly.

Name the deck and export it alone or together with other effects using Export
all. Custom thumbnails work; automatic thumbnails use the first frame.

All new exports share the animation-compatible renderer. Older lenticular mods
need a compatibility update or a fresh export before combining them with these
mods. Do not enable both an original mod and its updated copy together.
''',
    'Classic lenticular': '''CLASSIC LENTICULAR

Choose Classic flip when you want two different pictures to change with the viewing angle.

1. Select Image A and Image B. Matching 512 × 2048 PNGs are ideal.
2. Align features you want to stay still, such as a central logo.
3. Choose Stretch, Crop to fill or Fit entire image. The background colour fills transparent areas and padding.
4. Give the deck a unique name and choose an optional custom thumbnail. The automatic thumbnail shows both graphics with a transparent surround.
5. Move the viewing-angle slider to preview the crossover. Fine lens bands and slight image overlap are intentional.
6. Save the project, then export the deck or a combined pack.

The preview does not simulate game lighting or the curved deck surface. Check the final flip in the game before sharing it.
''',
    '3D depth map': '''3D WITH AN IMAGE AND DEPTH MAP

Choose 3D · image + depth map for depth within one complete picture. It needs a colour image and a matching grayscale depth map, not two different pictures.

PREPARE THE SOURCES
Use the same canvas, crop and alignment for both files. White means near and black means far. Smooth gradients describe rounded surfaces; clean boundaries separate objects. A blurry boundary can stretch the background across a foreground edge. Reverse depth swaps near and far if your map uses the opposite convention.

ADJUST THE EFFECT
Depth strength controls the separation between views. Start around 4–8%, then raise it while checking edges. The available 0–100% range is a control range, not a quality recommendation: large values can produce stretched or missing detail.

Stationary depth chooses the gray level that stays still. At 50%, middle gray stays still while nearer and farther regions move in opposite directions.

Lens texture controls variation between the fine lens bands. Keep some texture for the feel of a physical lenticular print. Setting it to zero removes band variation; it does not recover lost source detail or remove overlap between neighboring views.

CHECK THE PREVIEW
Move slowly through the front-facing angle. Look for depth, stable object shapes, visible fine bands and an acceptable crossover. Compare both directions. If outlines split, reduce depth strength before increasing lens texture. A single source image cannot reveal scenery hidden behind an object; newly exposed regions use a conservative edge fill.

EXPORT AND TEST
Save each deck as its own project with a unique name. Export saved deck pack combines several projects. Test each deck in the board menu, gameplay and Board Break. The current depth-map baseline has passed a menu/gameplay check; Board Break and classic flip were confirmed by the tester. Check your own artwork and settings in the game.

The candidate keeps eight views in the original texture allocation, arranged in two columns. Each view has 252 × 1004 pixels plus edge padding. This trades some horizontal resolution for twice the previous vertical detail; it does not create detail absent from the source.
''',
    'Layers and exporting': '''FOREGROUND / BACKGROUND — EXPERIMENTAL

This workflow is separate from image + depth map. Supply a transparent foreground PNG and a complete background image. Keep both canvases aligned.

Background motion sets the movement split: 0% moves the foreground, 50% balances both, and 100% moves the background. Depth strength sets the total separation. These form two flat depth planes; they do not infer rounded shapes inside the character.

The current export moves the two layers continuously in the shader and stores transparency in a separate mask. It preserves full image width and avoids blending between eight flattened images. The menu test is promising; per-section shifting in gameplay is still being investigated. This mode remains experimental. Do not confuse the layered image with a generated depth map.

COMBINED PACKS
Save all desired projects, then choose Export saved deck pack, or export decks as separate mods. Five decks across two separate mods passed the first coexistence check on ReSkate 2.1.0. The creator has no fixed five-deck cap; larger collections still depend on game resources. Use distinct names for now: persistent project identities and duplicate-name handling are still being developed.

Import the exported .fbmod into the shader-capable Studio build. Replace the previous version when updating the same mod; separate deck mods can coexist. Keep the old Lenticular_Camera_Probe disabled and preserve your Board Break / concave settings. The creator exports files locally; it does not install or enable mods.

TROUBLESHOOTING
Wrong depth direction: check Reverse depth.
Distorted shapes: confirm matching source alignment and reduce depth strength.
Soft detail: check source resolution and view packing; extra strength cannot sharpen it.
Missing board or startup failure: return to your last working export. Update the creator and re-export older crashing decks: generated texture IDs now avoid the reserved ResourceRef tag. Compiling successfully is not proof that a new build will load in game.
Texture rejected: retain the required dimensions and mip count.

Keep your source files with the project. Projects reference those files rather than embedding them. Reopen the creator after an update to load the latest controls.
''',
}

def open_guide(parent):
    window = tk.Toplevel(parent)
    window.title('ReSkate Deck Tool - Beta — Guide')
    window.geometry('760x680')
    notebook = ttk.Notebook(window)
    notebook.pack(fill='both', expand=True, padx=12, pady=12)
    for title, content in GUIDES.items():
        frame = ttk.Frame(notebook)
        text = ScrolledText(frame, wrap='word', font=('Segoe UI', 11),
                            padx=16, pady=16, relief='flat')
        text.insert('1.0', content)
        text.configure(state='disabled')
        text.pack(fill='both', expand=True)
        notebook.add(frame, text=title)
    return window

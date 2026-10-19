
# ReSkate Deck Tool

This is a tool for creating lenticular effect decks

The source code is here, we had to use ai assistance to finally get the damn thing working, so any help removing the ai code and getting it fully human would be greatly appreciated





### Updating older deck packs

New exports include the sticker compatibility fix for lenticular, depth-map,
foreground/background and animated decks. To update existing packs, choose
**File > Update existing FBMODs...**, select one or more Deck Tool exports, then
choose an output folder. The tool creates `- Compatible.fbmod` copies and keeps
original files unchanged. Import the copies in shader-capable ReSkate Studio,
replacing the older versions in your mod list. Update all older effect packs
that you enable together, as they share renderer resources.

The updater supports recognised Deck Tool renderers and uncompressed creator
exports. It skips unsupported files with an explanation; it does not convert
arbitrary third-party mods. The sticker fix preserves original artwork pixels,
uses full-resolution artwork separately from stickers, and keeps effect motion
on intact and broken boards. The gameplay lighting/darkness issue is still
being investigated.


### Important: repairing v0.1.5-beta.1 exports

Version v0.1.5-beta.1 wrote an incorrect FBMOD resource count. Studio could omit
five resources, breaking effects or stickers. I am very sorry for shipping this
and for the time wasted updating and testing packs.

Use v0.1.5-beta.3 or newer. Run affected files through **File > Update existing
FBMODs...**, then import the repaired copies in ReSkate Studio and replace the
broken versions. You can update the affected FBMOD directly; project files and
source images are not required. Originals stay unchanged. Files from the earlier
working in-game tests are unaffected.


### Standalone sticker fix: v0.1.5-beta.3

Beta.3 fixes a missing global texture registration that made beta.1/beta.2 packs
depend on a development probe mod. The repaired packs have been checked in game
with Sticker Mask Probe disabled: scrolling, animation, stickers, lenticular,
depth and foreground/background effects work and retain sharpness.

For packs exported or updated with beta.1/beta.2, use beta.3's **File > Update
existing FBMODs...**, then import the repaired copies and replace the older
versions in ReSkate Studio. No project files or source images are needed.
New beta.3 exports include both the resource-count and global-texture fixes.
Do not install a probe mod as a dependency or workaround.

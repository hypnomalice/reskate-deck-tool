
# ReSkate Deck Tool

Create Animated / GIF, Lenticular, Depth Map, Foreground / Background and Ghost Rare decks for ReSkate.

The source code is here, we had to use ai assistance to finally get the damn thing working, so any help removing the ai code and getting it fully human would be greatly appreciated





### Shared effects runtime — 1.1 test build

New exports contain artwork and settings, with `ReSkate Effects Runtime.fbmod`
saved beside them. Import the runtime once in ReSkate Studio, then import your
content packs. Effects are maintained in the runtime; older migrated content
keeps its existing format when effects are added.

For existing packs, choose **File > Migrate older packs (once)…**. Import the
new content copies and disable their old bundled versions. Originals are kept.
Use **File > Effects runtime setup…** to save an updated runtime for import.
There is no repeated “fix FBMOD compatibility” step for migrated content.

The runtime and converted packs have passed user testing with Animated Skulls
Croptop 1.0.0, including reversed order, stickers and Board Break. This verifies
that specific combination, not every third-party shader. Shared native shader
identities remain; automatic launcher installation and dependency enforcement
are not yet included. See [runtime details](docs/shared-runtime.md).

### Previous release history

The following repair instructions describe older releases and their standalone
exports. The shared-runtime build uses the one-time migration above instead.

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


### Version 1.0

The first full release includes Ghost Rare with silver shading, depth-guided
holographic colour and smooth depth motion. New projects start in Animated / GIF.
Depth Map and Foreground / Background are smooth by default, with an optional
**Enable lenticular** setting. Lenticular keeps the stepped lens effect; Ghost
Rare always stays smooth. Older saved projects retain their previous behaviour.

**Update older effect packs you use together** with File > Update existing
FBMODs, then re-import the compatible copies in shader-capable ReSkate Studio.
The packs share a renderer: an older pack above a new one can override support
for Ghost Rare and smooth depth. Until all packs are updated, keep a 1.0 export
above older effect packs in the mod load order. Neither Ghost Rare Prototype nor
Sticker Mask Probe is required.

**Known issues:** shadows and banding in gameplay remain unresolved. Work on
resolving both will continue in a future update. Preview lighting differs from
in-game lighting. Clean-machine testing remains pending.


### Version 1.0.1 performance update

Smooth-depth and Ghost Rare CPU previews avoid processing unused colour channels
while sampling depth. Development-PC benchmarks at the normal preview size
improved from 132 to 56 ms per frame for smooth depth and 210 to 84 ms for Ghost
Rare. Twelve before/after reference images were pixel-identical. These measure
preview rendering, not export speed or game FPS.

GIF placement edits reuse decoded frames when the source file is unchanged;
replacing the source file refreshes the cache. No game shaders or exported deck
formats changed, and existing FBMODs do not need updating for 1.0.1.
Shadows and banding in gameplay remain known issues. Ghost Rare masks are not
included in this update.

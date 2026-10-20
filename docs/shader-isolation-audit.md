# Deck scope and compatibility audit

The tool targets deck underside artwork. Clothing and griptape editing are not
part of the requested scope. A cosmetic target selector would not by itself
isolate shared shader resources.

Current exports create private per-deck preset, texture and material identities.
The effect shaders recognize a four-colour header signature in the custom atlas
and combine that check with the native material surface flag. The compositor
Lua recognizes the tool's deck-bottom preset names. Ordinary textures lacking
the signature do not intentionally enter the custom effect path.

The six compiled program resources still use shared identities, however. A
second mod replacing those same programs can conflict through load order even
when its textures and materials have different names. Signature recognition
prevents accidental effect activation; it does not solve program replacement
conflicts. An animated clothing/griptape mod must be compared at the resource
and shader-state table level before claiming compatibility. No renderer changes
or FBMOD migrations have been introduced by this audit.

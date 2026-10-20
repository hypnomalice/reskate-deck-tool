# Automatic updates

In the packaged Windows app, the update button downloads the standalone EXE from
this repository's GitHub release. The release must provide its expected size
and SHA-256 digest. Downloading and verification run in the background.

Unsaved work uses the existing Save / Discard / Cancel prompt before downloading.
A failed download leaves the running app in place. Once verified, a copy of the
current executable acts as a helper: it waits for Windows to release the app,
keeps the previous executable as `<tool>.exe.previous`, installs the new one and
restarts it. Failure to move or start the replacement restores the original.
The restarted app cleans up the known temporary helper files.

A folder that cannot be written reports an error; the updater does not request
administrator access or change permissions. Source-code runs and releases
without verifiable standalone assets open the release page instead.

Existing 1.0.1 installations still open the release page. Users must install a
version containing the updater once before future updates can replace it.
No FBMODs or game shaders are changed by the updater.

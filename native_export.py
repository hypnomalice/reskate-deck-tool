"""Compile content-only deck exports with an installed Studio CLI, without its UI.

The compiler is external and explicitly selected; it is never downloaded or
bundled. Compilation is staged separately; folder export writes only its selected mod.
"""
from pathlib import Path
import os
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile

RECEIPT = '.deck-tool-export.json'


def _digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_folder(destination):
    """Only replace an intact export owned by this tool, never another mod."""
    target = Path(destination).absolute()
    if target.is_symlink() or getattr(target, 'is_junction', lambda: False)():
        raise ValueError('Choose a normal mod folder, not a linked folder.')
    if not target.exists():
        return
    try:
        receipt = json.loads((target/RECEIPT).read_text(encoding='utf-8'))
        if receipt['tool'] != 'reskate-deck-tool' or receipt['format'] != 1:
            raise ValueError()
        expected = receipt['files']
        if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in target.rglob('*')):
            raise ValueError()
        actual = {p.relative_to(target).as_posix(): p for p in target.rglob('*') if p.is_file() and p.relative_to(target).as_posix() != RECEIPT}
        if set(actual) != set(expected):
            raise ValueError()
        for name, path in actual.items():
            if path.is_symlink() or not path.resolve().is_relative_to(target.resolve()) or _digest(path) != expected[name]:
                raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('This folder is not an unchanged Deck Tool export. Choose a new mod folder; existing files were left alone.') from None


def mod_name(title):
    name = re.sub(r'[^A-Za-z0-9 _.-]+', '_', title).strip(' .')[:64]
    if not name or name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        name = 'Deck Pack'
    return name


def validate_inputs(game_root, compiler):
    game, cli = Path(game_root).resolve(), Path(compiler).resolve()
    if not (game/'Skate.exe').is_file() or not (game/'Data/layout.toc').is_file():
        raise ValueError('Choose the Skate folder containing Skate.exe and Data/layout.toc.')
    if not cli.is_file():
        raise ValueError('Choose reskate_cli.exe from your shader-capable ReSkate Studio installation.')
    return game, cli


def export_zip(projects, destination, progress=lambda message: None, *, title, author='', game_root, compiler):
    import creator_engine
    game, cli = validate_inputs(game_root, compiler)
    target = Path(destination).resolve()
    if target.suffix.lower() != '.zip':
        raise ValueError('Choose a .zip file for a ready-to-install mod.')
    target.parent.mkdir(parents=True, exist_ok=True)
    # A private temporary tree prevents failed builds from replacing an existing
    # export or leaving half a mod in the game's Mods folder.
    with tempfile.TemporaryDirectory(prefix='.deck-native-') as temporary:
        root = Path(temporary)
        content = root/'content.fbmod'
        creator_engine.export_pack(projects, content, progress, title=title, author=author, shared_runtime=True)
        progress('Compiling installable mod files; Studio stays closed…')
        stage = root/'compiled'
        result = subprocess.run([str(cli), 'compile-mod', str(game), str(stage), str(content)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
            timeout=900, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise ValueError('Native mod compilation failed. Your previous export is unchanged.\n\n'+result.stdout[-6000:])
        patch = stage/'Patch'
        if patch.is_symlink() or not (patch/'layout.toc').is_file():
            raise ValueError('The compiler did not produce a native mod layout. Your previous export is unchanged.')
        files = sorted(p for p in patch.rglob('*') if p.is_file())
        if any(p.is_symlink() or not p.resolve().is_relative_to(patch.resolve()) for p in files):
            raise ValueError('The compiler output contains an unexpected linked file.')
        progress('Packing ready-to-install ZIP…')
        with tempfile.TemporaryDirectory(prefix='.deck-package-', dir=target.parent) as transfer:
            archive = Path(transfer)/'export.zip'
            name = mod_name(title)
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
                hashes = {}
                for file in files:
                    relative = file.relative_to(patch).as_posix()
                    zipped.write(file, name+'/'+relative)
                    hashes[relative] = _digest(file)
                readme = (
                    f'{title}\n\nInstall this ZIP through the ReSkate launcher, or extract its {name} folder into Mods. '
                    'Keep one current SDEC core enabled alongside this content pack.\n'
                    'SDEC is installed separately from Thunderstore; it is not downloaded or bundled here.\n'
                    'https://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/\n')
                zipped.writestr(name+'/DECK TOOL README.txt', readme)
                hashes['DECK TOOL README.txt'] = hashlib.sha256(readme.encode('utf-8')).hexdigest()
                zipped.writestr(name+'/'+RECEIPT, json.dumps(dict(tool='reskate-deck-tool', format=1, files=hashes), indent=2))
            with zipfile.ZipFile(archive) as zipped:
                if zipped.testzip() is not None:
                    raise ValueError('The native export ZIP failed verification.')
            os.replace(archive, target)
    progress('Installable mod ZIP exported.')
    return target


def export_folder(projects, destination, progress=lambda message: None, **options):
    """Export native content directly, backing up intact previous tool exports."""
    target = Path(destination).absolute()
    check_folder(target)
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.deck-folder-build-') as temporary:
        archive = Path(temporary)/'native.zip'
        export_zip(projects, archive, progress, **options)
        with tempfile.TemporaryDirectory(prefix='.deck-folder-stage-', dir=target.parent) as staged:
            staged = Path(staged)
            ready = staged/'new'
            ready.mkdir()
            prefix = mod_name(options['title'])+'/'
            with zipfile.ZipFile(archive) as zipped:
                for entry in zipped.infolist():
                    if not entry.filename.startswith(prefix):
                        raise ValueError('Unexpected mod folder in the generated ZIP.')
                    relative = Path(entry.filename[len(prefix):])
                    if relative.is_absolute() or '..' in relative.parts:
                        raise ValueError('Unexpected mod path in the generated ZIP.')
                    path = ready/relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with zipped.open(entry) as source, path.open('wb') as output:
                        shutil.copyfileobj(source, output)
            check_folder(ready)
            check_folder(target)  # do not overwrite edits made during compilation
            previous = staged/'previous'
            if target.exists():
                backups = target.parent/'.deck-tool-backups'
                if backups.is_symlink() or getattr(backups, 'is_junction', lambda: False)():
                    raise ValueError('The backup folder is linked; choose a different output folder.')
                backups.mkdir(exist_ok=True)
                backup = backups/(target.name+'-'+uuid.uuid4().hex[:12]+'.zip')
                with zipfile.ZipFile(backup, 'w', zipfile.ZIP_DEFLATED) as zipped:
                    for path in sorted(target.rglob('*')):
                        if path.is_file():
                            zipped.write(path, target.name+'/'+path.relative_to(target).as_posix())
                with zipfile.ZipFile(backup) as zipped:
                    if zipped.testzip() is not None:
                        raise ValueError('Previous mod backup failed verification; no files were replaced.')
                check_folder(target)
                os.replace(target, previous)
            try:
                os.replace(ready, target)
            except Exception:
                if previous.exists() and not target.exists():
                    os.replace(previous, target)
                raise
    progress('Native mod folder exported. Enable it in the launcher.')
    return target

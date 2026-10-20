import json
import re
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlsplit, quote
from urllib.request import Request, urlopen

from app_version import APP_VERSION

REPOSITORY = 'hypnomalice/reskate-deck-tool'
RELEASES_API = f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=20'


def version_key(tag):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)(?:[.-]?(\d+))?)?', str(tag))
    if not match:
        return None
    major, minor, patch, stage, revision = match.groups()
    return (int(major), int(minor), int(patch),
            {'alpha': 0, 'beta': 1, 'rc': 2, None: 3}[stage], int(revision or 0))


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    download_url: str = ""
    sha256: str = ""
    size: int = 0


def newer_release(releases, current=APP_VERSION):
    current_key = version_key(current)
    if current_key is None or not isinstance(releases, list):
        return None
    candidates = []
    for item in releases:
        if not isinstance(item, dict) or item.get('draft'):
            continue
        tag = item.get('tag_name', '')
        key = version_key(tag)
        if key is None or key <= current_key:
            continue
        if current_key[3] == 3 and (item.get('prerelease') or key[3] != 3):
            continue
        url = item.get('html_url', '')
        if not isinstance(url, str):
            continue
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.netloc != 'github.com'
                or parsed.path != f'/{REPOSITORY}/releases/tag/{tag}'
                or parsed.query or parsed.fragment):
            continue
        download, digest, size = '', '', 0
        for asset in item.get('assets',[]) or []:
            if not isinstance(asset,dict) or asset.get('name') not in ('ReSkate Deck Tool.exe','ReSkate.Deck.Tool.exe'):
                continue
            link=asset.get('browser_download_url','')
            parsed_asset=urlsplit(link)
            checksum=asset.get('digest','') or ''
            length=asset.get('size',0)
            if (parsed_asset.scheme=='https' and parsed_asset.netloc=='github.com'
                    and parsed_asset.path==f"/{REPOSITORY}/releases/download/{tag}/{quote(asset['name'])}"
                    and not parsed_asset.query and not parsed_asset.fragment
                    and re.fullmatch(r'sha256:[0-9a-f]{64}',checksum)
                    and isinstance(length,int) and 0<length<=200_000_000):
                download,digest,size=link,checksum[7:],length
        candidates.append((key, Release(tag, url, download, digest, size)))
    return max(candidates, key=lambda pair: pair[0])[1] if candidates else None


def check_for_update(current=APP_VERSION):
    request = Request(RELEASES_API, headers={
        'User-Agent': f'ReSkate-Deck-Tool/{current}',
        'Accept': 'application/vnd.github+json',
    })
    try:
        with urlopen(request, timeout=5) as response:
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            return None
        return newer_release(json.loads(payload), current)
    except (URLError, OSError, ValueError):
        return None


def download_update(release, folder, progress=lambda done,total:None):
    """Download a release to staging; never alter the running application."""
    import hashlib
    from pathlib import Path
    if not release.download_url or not re.fullmatch(r'[0-9a-f]{64}',release.sha256) or not 0<release.size<=200_000_000:
        raise ValueError('This release does not provide a verified automatic download.')
    destination=Path(folder)/'update.exe'
    partial=Path(folder)/'update.partial'
    try:
        digest=hashlib.sha256();done=0
        request=Request(release.download_url,headers={'User-Agent':f'ReSkate-Deck-Tool/{APP_VERSION}'})
        with urlopen(request,timeout=30) as source,partial.open('wb') as target:
            while True:
                block=source.read(1024*1024)
                if not block:break
                done+=len(block)
                if done>release.size:raise ValueError('The update size does not match the release.')
                target.write(block);digest.update(block);progress(done,release.size)
        if done!=release.size or digest.hexdigest()!=release.sha256:
            raise ValueError('The update failed verification. Your installed tool was not changed.')
        partial.replace(destination)
        return destination
    finally:
        partial.unlink(missing_ok=True)


def stage_install(download, target, digest):
    """Run a copy of our current application as the updater helper."""
    import hashlib,shutil,subprocess
    from pathlib import Path
    download,target=Path(download).resolve(),Path(target).resolve()
    if download==target or hashlib.sha256(download.read_bytes()).hexdigest()!=digest:
        raise ValueError('The staged update is invalid.')
    import tempfile
    with tempfile.TemporaryFile(dir=target.parent):
        pass
    helper=download.parent/'installer.exe'
    if helper.exists():raise ValueError('An update is already staged in this folder.')
    shutil.copy2(target,helper)
    request=download.parent/'install.json'
    request.write_text(json.dumps(dict(download=str(download),target=str(target),sha256=digest)),encoding='utf8')
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    subprocess.Popen([str(helper),'--install-update',str(request)],creationflags=flags,cwd=str(target.parent))


def apply_update(request_path):
    """Helper mode: wait for Windows to release the EXE, replace, then restart."""
    import hashlib,os,subprocess,time
    from pathlib import Path
    request_path=Path(request_path).resolve()
    data=json.loads(request_path.read_text(encoding='utf8'))
    source=Path(data['download']).resolve();target=Path(data['target']).resolve()
    if source.parent!=request_path.parent or source==target or target.suffix.lower()!='.exe':
        raise ValueError('Invalid update paths.')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=data['sha256']:
        raise ValueError('The staged update failed verification.')
    backup=target.with_name(target.name+'.previous')
    deadline=time.monotonic()+60
    while True:
        try:
            os.replace(target,backup)
            break
        except PermissionError:
            if time.monotonic()>=deadline:raise TimeoutError('Close the tool and try the update again.')
            time.sleep(.25)
    try:
        os.replace(source,target)
    except OSError:
        os.replace(backup,target)
        raise
    try:
        subprocess.Popen([str(target),'--cleanup-update',str(request_path)],cwd=str(target.parent))
    except OSError:
        os.replace(target,source)
        os.replace(backup,target)
        raise
    return target


def cleanup_update(request_path):
    """Remove only the known staging files after the helper exits."""
    import tempfile,time
    from pathlib import Path
    folder=Path(request_path).resolve().parent
    if folder.parent!=Path(tempfile.gettempdir()).resolve() or not folder.name.startswith('reskate-update-'):
        return
    deadline=time.monotonic()+15
    while True:
        try:
            for name in ('installer.exe','install.json','update.partial'):
                (folder/name).unlink(missing_ok=True)
            folder.rmdir()
            return
        except PermissionError:
            if time.monotonic()>=deadline:return
            time.sleep(.25)
        except OSError:
            return

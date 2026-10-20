import hashlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from updates import Release,newer_release,download_update,apply_update

class AutomaticUpdateTests(unittest.TestCase):
    def asset_release(self,data=b'new app'):
        return Release('v1.0.2','https://github.com/hypnomalice/reskate-deck-tool/releases/tag/v1.0.2','https://github.com/hypnomalice/reskate-deck-tool/releases/download/v1.0.2/ReSkate.Deck.Tool.exe',hashlib.sha256(data).hexdigest(),len(data))

    def test_only_expected_repository_executable_with_digest_is_installable(self):
        r=self.asset_release()
        item=dict(tag_name=r.version,html_url=r.url,assets=[dict(name='ReSkate.Deck.Tool.exe',browser_download_url=r.download_url,digest='sha256:'+r.sha256,size=r.size)])
        self.assertEqual(newer_release([item],'1.0.1').download_url,r.download_url)
        item['assets'][0]['browser_download_url']='https://example.com/app.exe'
        self.assertFalse(newer_release([item],'1.0.1').download_url)
        item['assets'][0]['browser_download_url']=r.download_url
        item['assets'][0]['digest']=''
        self.assertFalse(newer_release([item],'1.0.1').download_url)

    def test_verified_download_and_corruption_cleanup(self):
        data=b'new app';r=self.asset_release(data)
        with tempfile.TemporaryDirectory() as folder:
            with patch('updates.urlopen',return_value=io.BytesIO(data)):
                self.assertEqual(download_update(r,folder).read_bytes(),data)
            for invalid in (b'bad app',b'too large update'):
                with patch('updates.urlopen',return_value=io.BytesIO(invalid)),self.assertRaises(ValueError):
                    download_update(r,folder)
                self.assertFalse((Path(folder)/'update.partial').exists())

    def request(self,folder):
        folder=Path(folder);source=folder/'update.exe';target=folder/'tool.exe'
        source.write_bytes(b'new app');target.write_bytes(b'old app')
        request=folder/'install.json';request.write_text(json.dumps(dict(download=str(source),target=str(target),sha256=hashlib.sha256(b'new app').hexdigest())))
        return request,source,target

    def test_replacement_retains_previous_and_restarts(self):
        with tempfile.TemporaryDirectory() as folder,patch('subprocess.Popen') as launch:
            request,source,target=self.request(folder);apply_update(request)
            self.assertEqual(target.read_bytes(),b'new app')
            self.assertEqual(target.with_name('tool.exe.previous').read_bytes(),b'old app')
            self.assertEqual(launch.call_args.args[0][0],str(target))

    def test_failed_restart_restores_original(self):
        with tempfile.TemporaryDirectory() as folder,patch('subprocess.Popen',side_effect=OSError('launch failed')):
            request,source,target=self.request(folder)
            with self.assertRaises(OSError):apply_update(request)
            self.assertEqual(target.read_bytes(),b'old app')
            self.assertEqual(source.read_bytes(),b'new app')

    def test_corrupt_staging_does_not_touch_original(self):
        with tempfile.TemporaryDirectory() as folder:
            request,source,target=self.request(folder);source.write_bytes(b'bad')
            with self.assertRaises(ValueError):apply_update(request)
            self.assertEqual(target.read_bytes(),b'old app')

import unittest
from unittest.mock import patch
from urllib.error import URLError

from updates import check_for_update, newer_release, version_key


def release(tag, **extra):
    return dict({'tag_name':tag, 'html_url':f'https://github.com/hypnomalice/reskate-deck-tool/releases/tag/{tag}'}, **extra)


class UpdateTests(unittest.TestCase):
    def test_numeric_order_and_beta_channel(self):
        rows = [release('v0.1.9-beta', prerelease=True), release('v0.1.10-beta', prerelease=True)]
        self.assertEqual(newer_release(rows,'0.1.8-beta').version,'v0.1.10-beta')
        self.assertIsNone(newer_release(rows,'0.1.10-beta'))
        self.assertGreater(version_key('0.1.10'),version_key('0.1.10-rc.2'))

    def test_drafts_unknown_tags_and_wrong_links_are_ignored(self):
        rows = [release('v1.0.0',draft=True), release('nightly'),
                release('v2.0.0',html_url='https://example.com/download')]
        self.assertIsNone(newer_release(rows,'0.1.4-beta'))

    def test_stable_users_are_not_offered_prereleases(self):
        rows = [release('v0.2.0-beta',prerelease=True),release('v0.1.5')]
        self.assertEqual(newer_release(rows,'0.1.4').version,'v0.1.5')

    def test_beta_can_upgrade_to_final(self):
        self.assertEqual(newer_release([release('v0.1.4')],'0.1.4-beta').version,'v0.1.4')

    @patch('updates.urlopen',side_effect=URLError('offline'))
    def test_offline_is_quiet(self, opener):
        self.assertIsNone(check_for_update())
        self.assertEqual(opener.call_args.kwargs['timeout'],5)


if __name__=='__main__':unittest.main()

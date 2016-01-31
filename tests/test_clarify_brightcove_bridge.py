import unittest
import httpretty
from clarify_python import clarify
from clarify_brightcove_sync.brightcove_api_client import BrightcoveAPIClient
from clarify_brightcove_sync.clarify_brightcove_bridge import ClarifyBrightcoveBridge
from . import register_uris


class TestClient(unittest.TestCase):

    def setUp(self):
        api_key = 'my-api-key'
        self.clarify_client = clarify.Client(api_key)
        self.brightcove_client = BrightcoveAPIClient(creds_file='brightcove_oauth.txt')

    def tearDown(self):
        self.clarify_client = None
        self.brightcove_client = None

    @httpretty.activate
    def test_sync(self):
        register_uris(httpretty)
        bridge = ClarifyBrightcoveBridge(self.clarify_client, self.brightcove_client)
        self.assertIsNotNone(bridge)

        def confirm_delete(name, video_id):
            return True

        bridge.sync_bundles(confirm_delete_fun=confirm_delete)
        bridge.log_sync_stats()
        latest_requests = httpretty.httpretty.latest_requests
        self.assertEqual(len(latest_requests), 9)
        self.assertEqual(bridge.sync_stats['created'], 1)
        self.assertEqual(bridge.sync_stats['updated'], 1)
        self.assertEqual(bridge.sync_stats['deleted'], 1)
        self.assertEqual(bridge.sync_stats['count'], 2)

    @httpretty.activate
    def test_sync_no_delete(self):
        register_uris(httpretty)
        bridge = ClarifyBrightcoveBridge(self.clarify_client, self.brightcove_client)
        self.assertIsNotNone(bridge)

        def confirm_delete(name, video_id):
            return False

        bridge.sync_bundles(confirm_delete_fun=confirm_delete)
        bridge.log_sync_stats()
        latest_requests = httpretty.httpretty.latest_requests
        self.assertEqual(len(latest_requests), 8)
        self.assertEqual(bridge.sync_stats['created'], 1)
        self.assertEqual(bridge.sync_stats['updated'], 1)
        self.assertEqual(bridge.sync_stats['deleted'], 0)
        self.assertEqual(bridge.sync_stats['count'], 3)

    @httpretty.activate
    def test_sync_metadata_synced(self):
        register_uris(httpretty, metadata_synced=True)
        bridge = ClarifyBrightcoveBridge(self.clarify_client, self.brightcove_client)
        self.assertIsNotNone(bridge)
        bridge.sync_bundles()
        bridge.log_sync_stats()
        latest_requests = httpretty.httpretty.latest_requests
        self.assertEqual(len(latest_requests), 8)
        self.assertEqual(bridge.sync_stats['created'], 1)
        self.assertEqual(bridge.sync_stats['updated'], 0)
        self.assertEqual(bridge.sync_stats['deleted'], 1)
        self.assertEqual(bridge.sync_stats['count'], 2)

    @httpretty.activate
    def test_sync_bc_errors(self):
        register_uris(httpretty, bc_videos_auth_error=True, bc_videos_throttle=True)

        bridge = ClarifyBrightcoveBridge(self.clarify_client, self.brightcove_client)
        self.assertIsNotNone(bridge)
        bridge.sync_bundles()
        bridge.log_sync_stats()
        latest_requests = httpretty.httpretty.latest_requests
        self.assertEqual(len(latest_requests), 12)
        self.assertEqual(bridge.sync_stats['created'], 1)
        self.assertEqual(bridge.sync_stats['updated'], 1)
        self.assertEqual(bridge.sync_stats['deleted'], 1)
        self.assertEqual(bridge.sync_stats['count'], 2)

    @httpretty.activate
    def test_sync_cfy_error(self):
        register_uris(httpretty, cfy_post_bundle_error=True)

        bridge = ClarifyBrightcoveBridge(self.clarify_client, self.brightcove_client)
        self.assertIsNotNone(bridge)
        with self.assertRaises(clarify.APIException):
            bridge.sync_bundles()

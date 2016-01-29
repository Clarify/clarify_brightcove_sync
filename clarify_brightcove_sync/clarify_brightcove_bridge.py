from collections import Counter
from clarify_python.helper import get_embedded_items, get_link_href

MAX_METADATA_STRING_LEN = 2000


def default_to_empty_string(val):
    return val if val is not None else ''


class ClarifyBrightcoveBridge:

    def __init__(self, clarify_client, bc_client):
        self.clarify_client = clarify_client
        self.bc_client = bc_client
        self.sync_stats = Counter(created=0, updated=0, deleted=0)
        self.dry_run = False

    def log(self, output_str):
        print(output_str)

    def log_sync_stats(self):
        print('\nBundle stats:')
        print('  created: {0}'.format(self.sync_stats['created']))
        print('  updated: {0}'.format(self.sync_stats['updated']))
        print('  deleted: {0}'.format(self.sync_stats['deleted']))
        print('  total:   {0}'.format(self.sync_stats['count']))

    def _load_bundle_map(self):
        '''
        Return a map of all bundles in the Clarify app that have an external_id set for them.
        The bundles with external_ids set are assumed to be the ones we have inserted from Brightcove.
        The external_id contains the Brightcove video id.
        '''
        bundle_map = {}
        next_href = None
        has_next = True

        while has_next:
            bundles = self.clarify_client.get_bundle_list(href=next_href, embed_items=True)
            items = get_embedded_items(bundles)
            for item in items:
                bc_video_id = item.get('external_id')
                if bc_video_id is not None and len(bc_video_id) > 0:
                    bundle_map[bc_video_id] = item
            next_href = get_link_href(bundles, 'next')
            if next_href is None:
                has_next = False
        return bundle_map

    def _metadata_from_video(self, video):
        '''Generate the searchable metadata that we'll store in the bundle for the video'''
        long_desc = video['long_description']
        if long_desc is not None:
            long_desc = long_desc[:MAX_METADATA_STRING_LEN]

        tags = video.get('tags')

        metadata = {
            'name': default_to_empty_string(video.get('name')),
            'description': default_to_empty_string(video.get('description')),
            'long_description': default_to_empty_string(long_desc),
            'tags': tags if tags is not None else [],
            'updated_at': video.get('updated_at'),
            'created_at': video.get('created_at'),
            'state': video.get('state')
        }
        return metadata

    def _src_media_url_for_video(self, video):
        '''Get the url for the video media that we can send to Clarify'''
        src_url = None
        best_height = 0
        best_source = None

        # TODO: This assumes we have ingested videos. For remote videos, check if the remote flag is True
        # and if so, use the src url from the Asset endpoint.
        video_sources = self.bc_client.get_video_sources(video['id'])
        # Look for codec H264 with good resolution
        for source in video_sources:
            height = source.get('height', 0)
            codec = source.get('codec')
            if source.get('src') and codec and codec.upper() == 'H264' and height <= 1080 and height > best_height:
                best_source = source

        if best_source is not None:
            src_url = best_source['src']
        return src_url

    def _create_bundle_for_video(self, video):

        media_url = self._src_media_url_for_video(video)
        if not media_url:
            self.log('SKIPPING: No suitable video src url for video {0} {1}'.format(video['id'], video['name']))
            return

        self.log('Creating bundle for video {0} {1}'.format(video['id'], video['name']))

        if not self.dry_run:
            external_id = video['id']
            name = video.get('original_filename')
            metadata = self._metadata_from_video(video)
            self.clarify_client.create_bundle(name=name, media_url=media_url,
                                              metadata=metadata, external_id=external_id)
        self.sync_stats['created'] += 1

    def _update_metadata_for_video(self, metadata_href, video):
        '''
        Update the metadata for the video if video has been updated in Brightcove since the bundle
        metadata was last updated.
        '''
        current_metadata = self.clarify_client.get_metadata(metadata_href)
        cur_data = current_metadata.get('data')

        if cur_data.get('updated_at') != video['updated_at']:
            self.log('Updating metadata for video {0}'.format(video['id']))
            if not self.dry_run:
                metadata = self._metadata_from_video(video)
                self.clarify_client.update_metadata(metadata_href, metadata=metadata)
            self.sync_stats['updated'] += 1

    def sync_bundles(self, delete_bundles=True, update_metadata=True, confirm_delete_fun=None, dry_run=False):

        self.dry_run = dry_run
        self.sync_stats.clear()

        if dry_run:
            self.log('-----------------------------------')
            self.log('DRY RUN - not modifying any bundles')
            self.log('-----------------------------------')

        self.log('Fetching bundles...')
        bundle_map = self._load_bundle_map()
        self.log('Fetching videos...')
        videos = self.bc_client.get_all_videos()

        self.log('Checking {0} videos...'.format(len(videos)))
        for video in videos:
            vid = video['id']
            bundle = bundle_map.get(vid)

            if bundle is None:
                # Create a bundle for the video
                self._create_bundle_for_video(video)

            elif update_metadata:
                # Update the metadata in the bundle for the video
                self._update_metadata_for_video(get_link_href(bundle, 'clarify:metadata'), video)

        if delete_bundles:
            self.log('Checking deleted videos...')
            # Delete bundles for missing videos
            existing_vids = set([x['id'] for x in videos])
            existing_bundles = set(bundle_map.keys())
            missing_bundles = existing_bundles - existing_vids
            if len(missing_bundles):
                for vid in missing_bundles:
                    bundle = bundle_map.get(vid)
                    if dry_run or confirm_delete_fun is None or \
                            confirm_delete_fun(bundle['name'], bundle['external_id']):
                        self.log('Delete bundle for video {0}'.format(bundle['external_id']))
                        if not dry_run:
                            self.clarify_client.delete_bundle(get_link_href(bundle, 'self'))
                        self.sync_stats['deleted'] += 1

        self.sync_stats['count'] = len(bundle_map) + self.sync_stats['created'] - self.sync_stats['deleted']
        self.log('done.')

import os
import re
from clarify_brightcove_sync.brightcove_api_client import BrightcoveAPIClient

clarify_host = 'https://api.clarify.io'


def load_body(filename):
    text = None
    with open(os.path.join('.', 'tests', 'data', filename), encoding="utf-8") as f:
        text = f.read()
    return text if text else '{}'


def register_uris(httpretty, metadata_synced=False, bc_videos_auth_error=False, bc_videos_throttle=False,
                  cfy_post_bundle_error=False):

    httpretty.HTTPretty.allow_net_connect = False

    responses = []
    if cfy_post_bundle_error:
        responses.append(httpretty.Response(body="{}", status=503, content_type='application/json'))
    else:
        responses.append(httpretty.Response(body=load_body('bundle_ref.json'), status=201,
                                            content_type='application/json'))

    httpretty.register_uri('POST', clarify_host + '/v1/bundles', responses=responses)

    httpretty.register_uri('GET', clarify_host + '/v1/bundles',
                           body=load_body('bundles_1.json'), status=200,
                           content_type='application/json')

    metadata_file = 'metadata_synced.json' if metadata_synced else 'metadata_empty.json'
    httpretty.register_uri('GET', re.compile(clarify_host + '/v1/bundles/(\w+)/metadata$'),
                           body=load_body(metadata_file), status=200,
                           content_type='application/json')

    httpretty.register_uri('PUT', re.compile(clarify_host + '/v1/bundles/(\w+)/metadata$'),
                           body='{}', status=202,
                           content_type='application/json')

    httpretty.register_uri('DELETE', re.compile(clarify_host + '/v1/bundles/(\w+)$'),
                           body='', status=204,
                           content_type='application/json')

    httpretty.register_uri('POST', 'https://oauth.brightcove.com/v3/access_token',
                           body=load_body('bc_access_token.json'), status=200,
                           content_type='application/json')

    httpretty.register_uri('GET', 'https://' + BrightcoveAPIClient.CMS_Server + '/v1/accounts//counts/videos',
                           body=load_body('bc_counts_videos.json'), status=200,
                           content_type='application/json')

    responses = []
    if bc_videos_auth_error:
        responses.append(httpretty.Response(body="{}", status=401, content_type='application/json'))
    if bc_videos_throttle:
        responses.append(httpretty.Response(body="{}", status=429, content_type='application/json'))
    responses.append(httpretty.Response(body=load_body('bc_videos.json'), status=200, content_type='application/json'))

    httpretty.register_uri('GET', 'https://' + BrightcoveAPIClient.CMS_Server + '/v1/accounts//videos',
                           responses=responses)

    httpretty.register_uri('GET', re.compile('https://' + BrightcoveAPIClient.CMS_Server +
                                             '/v1/accounts//videos/(\w+)/sources$'),
                           body=load_body('bc_video_sources.json'), status=200,
                           content_type='application/json')

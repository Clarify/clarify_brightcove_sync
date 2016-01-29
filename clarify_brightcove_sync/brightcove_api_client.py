import requests
import math
import time
import base64
import json
import sys
import os

# -------------------------------------------------
# Based on a Brightcove sample test script.
# - ported to Python 3
# - Made into a class
# - Added API access functions
# - Added error handling
# -------------------------------------------------

# This is a python script to test the CMS API.
# To use this script, edit the configuration file brightcove_oauth.json
# with your brightcove account ID, and a client ID and client secret for
# an Oauth credential that has CMS API - Videos Read permission.
# You can find instructions on how to generate Oauth credentials
# http://docs.brightcove.com/en/video-cloud/cms-api/getting-started/quick-start-cms.html

# This script demonstrates how to refresh the access token
# in handling 401 - Unauthorized errors from the CMS API
# Because the Oauth tokens have a 300 second time to live,
# The refresh logic to handle 401 errors will be a normal part of runtime behavior.

# Note that the client_id and client_secret secure the access to the CMS API
# Therefore, it is not advisable to expose them to browsers. These are meant for
# server to server communication to obtain an access token.

# The access token can be exposed to the browser. Its limited permissions and expiry
# time make limit the duration and scope of its usage should it be observed in network
# traffic or obtained from a browser.


def add_param_if_not_none(params, param, val):
    if val is not None:
        params[param] = val


class AuthError(Exception):
    def __init__(self):
        super().__init__('Brightcove Auth Error')


class TooManyRequestsError(Exception):
    def __init__(self):
        super().__init__('Brightcove Too Many Requests')


class BrightcoveAPIClient:
    CMS_Server = "cms.api.brightcove.com"
    Ingest_Server = "ingest.api.brightcove.com"

    def __init__(self, creds_file='brightcove_oauth.json'):
        self.credentials = self._load_secret(creds_file)
        self.current_token = None

    def _load_secret(self, creds_file):
        '''read the oauth secrets and account ID from a credentials configuration file'''
        try:
            with open(creds_file) as fp:
                creds = json.load(fp)
            return creds
        except Exception as e:
            sys.stderr.write("Error loading oauth secret from local file called '{0}'\n".format(creds_file))
            sys.stderr.write("\tThere should be a local OAuth credentials file \n")
            sys.stderr.write("\twhich has contents like this:\n")
            sys.stderr.write("""
                {
                "account_id": "1234567890001",
                "client_id": "30ff0909-0909-33d3-ae88-c9887777a7b7",
                "client_secret": "mzKKjZZyeW5YgsdfBD37c5730g397agU35-Dsgeox6-73giehbt0996nQ"
                }

              """)
            sys.stderr.write("\n")
            raise e

    # get the oauth 2.0 token
    def _get_auth_token(self, creds):

        url = "https://oauth.brightcove.com/v3/access_token"

        params = {
            "grant_type": "client_credentials"
        }

        client = creds["client_id"]
        client_secret = creds["client_secret"]

        authString = base64.encodebytes('{0}:{1}'.format(client, client_secret).encode('utf-8')) \
            .decode('ascii').replace('\n', '')

        headersMap = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic " + authString
        }

        response = requests.post(url, params=params, headers=headersMap)

        if response.status_code == 200:
            result = response.json()
            return result["access_token"]

    # call CMS API
    def _try_request(self, token, account, server, method, requestUrl, params=None, data=None):

        requestUrl = 'https://' + server + requestUrl

        headersMap = {
            "Authorization": "Bearer " + token
        }

        if data is not None and isinstance(data, dict):
            headersMap["Content-Type"] = "application/json"
            data = json.dumps(data)

        response = requests.request(method, requestUrl, params=params, data=data, headers=headersMap)
        result = response.json()

        if response.status_code >= 200 and response.status_code <= 299:
            return result
        elif response.status_code == 401:
            # if we get a 401 it is most likely because the token is expired.
            raise AuthError()
        elif response.status_code == 429:
            raise TooManyRequestsError()
        elif response.status_code == 500 and len(result) > 0 and result[0].get('error_code') == 'TIMEOUT':
            raise TooManyRequestsError()
        else:
            sys.stderr.write("Error: " + requestUrl + "\n")
            sys.stderr.write(response.text)
            sys.stderr.write("\n")
            raise Exception('API_CALL_ERROR' + " error " + str(response.status_code))

    def _make_request(self, server, method, urlSubPath, params=None, data=None):

        if (not self.current_token):
            self.current_token = self._get_auth_token(self.credentials)

        account = self.credentials["account"]

        requestUrl = "/v1/accounts/" + account + urlSubPath

        while self.current_token:
            try:
                return self._try_request(self.current_token, account, server, method, requestUrl, params, data)
            except TooManyRequestsError:
                # Sleep and try again...
                time.sleep(1)
            except AuthError:
                # handle an auth error by re-fetching a auth token again
                self.current_token = self._get_auth_token(self.credentials)

        raise AuthError()

    def get_video_count(self, search_q=None):
        '''Return the number of videos in the account'''
        if search_q is not None:
            params = {'q': search_q}
        else:
            params = None

        url = "/counts/videos"
        result = self._make_request(self.CMS_Server, 'GET', url, params=params)
        return result['count']

    def get_videos(self, limit=None, offset=None, search_q=None, sort=None):

        if limit is not None or offset is not None or search_q is not None or sort is not None:
            params = {}
            add_param_if_not_none(params, 'limit', limit)
            add_param_if_not_none(params, 'offset', offset)
            add_param_if_not_none(params, 'q', search_q)
            add_param_if_not_none(params, 'sort', sort)
        else:
            params = None

        url = '/videos'
        result = self._make_request(self.CMS_Server, 'GET', url, params=params)
        return result

    def get_all_videos(self, search_q=None):
        '''
        Gets all the videos in an account by automatically paginating through getVideos().
        WARNING: Use with caution if you have thousands of videos!
        WARNING: If deletes are being done during this iteration, the list may be missing videos.
        '''
        page_size = 10
        current_page = 0
        total_count = self.get_video_count(search_q=search_q)
        total_page = math.ceil(total_count / page_size)
        # We sort by 'created_at' so any newly added videos will be on the last page.
        # We don't currently handle deletes during the iteration which could cause videos to be missed.
        sort = 'created_at'
        result = []
        while current_page < total_page:
            page_result = self.get_videos(limit=page_size, offset=current_page * page_size,
                                          search_q=search_q, sort=sort)
            result += page_result
            current_page += 1
        return result

    def get_video_sources(self, bcVideoId):
        url = '/videos/' + bcVideoId + '/sources'
        result = self._make_request(self.CMS_Server, 'GET', url)
        return result

    def post_video(self, videoUrl, name=None, ingestMedia=True):
        '''Post and optionally ingest media from the specified URL'''
        if name is None:
            name = os.path.basename(videoUrl)

        url = '/videos'
        data = {'name': name}
        new_video = self._make_request(self.CMS_Server, 'POST', url, data=data)
        if ingestMedia:
            self.ingest_video(new_video['id'], videoUrl)
        return new_video

    def ingest_video(self, bcVideoId, videoUrl):
        '''Returns something like {'id': 'e99451a5-1a09-4258-8e73-798c9b58f126'}'''

        ingestData = {
            "master": {"url": videoUrl},
            "profile": "balanced-nextgen-player"  # "balanced-high-definition"
        }
        url = '/videos/' + bcVideoId + '/ingest-requests'
        result = self._make_request(self.Ingest_Server, 'POST', url, data=ingestData)
        return result

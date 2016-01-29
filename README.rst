.. image:: https://travis-ci.org/Clarify/clarify_brightcove_sync.svg
   :target: https://travis-ci.org/Clarify/clarify_brightcove_sync

===============================
Clarify Brightcove Sync Tool
===============================

Automatically send your Brightcove data to Clarify.

This is a simple tool for sending the content of a Brightcove (http://www.brightcove.com) video library to Clarify (http://clarify.io), including the media and metadata.

The Clarify API analyzes media for words spoken and makes it searchable. It can also automatically generate extra metadata such as keywords and topics.

Running the sync tool will compare the contents of your Brightcove library and your Clarify account app. Any new videos will be added as a new bundle in Clarify, with the media and metadata from Brightcove. Videos that have been updated in Brightcove since the last sync will have their corresponding bundle metadata updated in Clarify. Any bundles that no longer have a corresponding video will be deleted (after prompting the user to confirm the delete.)

This script does not modify content in Brightcove so does NOT require Brightcove API write access.

* Requires Python 3 (yeah!)
* If you have a very large or rapidly changing video library, see `Limitations`_ below.
* Free software: MIT license

Installing
----------

This script requires Python 3.4 or above. Make sure the pip you are running corresponds to Python 3.x and not Python 2.x.

.. code-block:: bash

   $ pip install clarify_brightcove_sync

You may need to use sudo if you don't have permission to install. If you are upgrading from an older version, use the --upgrade flag.


Quickstart Guide
----------------

You must configure the authentication credentials for your Brightcove and Clarify accounts.

Brightcove Credentials
^^^^^^^^^^^^^^^^^^^^^^

To get Brightcove API credentials:

* Log in to https://studio.brightcove.com
* In the ``ADMIN`` menu, choose ``API Authentication``
* Click ``Register New Application`` button
* This will bring up a form
    + In the ``Name`` field enter ``Clarify Brightcove Sync``
    + Select your account for authorization
    + Enable the ``Video Read`` permissions for the CMS API
    + Click Save
    + Copy the ``Client Secret`` and store it in a safe place
    + Copy the ``Client ID`` and store it in a safe place as well
* Now go back to the ``ADMIN`` menu and choose ``Account Information``
* Copy your Account number, we will use it in the next steps.

Now we have the credentials we need to store them in a config file:

* Open a new file in your editor and enter the following text
.. code-block::

       {
	    "account": "",
	    "client_id": "",
	    "client_secret": ""
       }

* Fill in the values for the ``Account`` number, ``Client ID``, and ``Client Secret``.
* Save the file as ``brightcove_oath.json``
* Set an environment variable ``BRIGHTCOVE_API_CREDENTIALS`` with the path to the ``brightcove_oath.json`` file. This path can be relative to the current working directory. Alternatively, you can pass the value on the commandline when you run the script as ``BRIGHTCOVE_API_CREDENTIALS=<file> clarify_brightcove_sync``.


Clarify Credentials
^^^^^^^^^^^^^^^^^^^

* Log in to the Clarify developer portal https://developer.clarify.io
* Go to ``Apps & Keys`` and copy the API Key for your app
* Set an environment variable ``CLARIFY_API_KEY`` with the value of your key. Alternatively, you can pass the value on the commandline when you run the  as ``CLARIFY_API_KEY=<secret> clarify_brightcove_sync``.
.. code-block:: bash

        $ export CLARIFY_API_KEY=secret_key

Running the Script
^^^^^^^^^^^^^^^^^^

It is recommended to run the script from a shell / command prompt. Make sure you are running Python 3.x and your environment is set up properly.

If everything is configured properly, you can simply run the following command to do a dry-run of a sync. This won't actually modify any data.

.. code-block:: bash

        $ clarify_brightcove_sync --dry_run

or if you are passing the credentials on the commandline:

.. code-block:: bash

        $ CLARIFY_API_KEY=<secret> BRIGHTCOVE_API_CREDENTIALS=<file> clarify_brightcove_sync --dry_run

If things look correct, you can run the sync for real to have Clarify bundles created, updated, and deleted as needed. Note that this will incur usage of credit in your Clarify account.

.. code-block:: bash

        $ clarify_brightcove_sync


Video Media
-----------

The Clarify API ingests media from URLs. This sync tool looks in the Sources (renditions) of a Brightcove Video to find one with the highest resolution (up to 1080p), encoded using the H264 codec, and featuring an http/https Src URL. If no suitable video URL is found, the bundle will not be created in Clarify. See `Limitations`_ for more details.

Metadata
--------

Video metadata from the Brightcove API is stored as Clarify bundle metadata so that it is searchable along with the spoken words. The following fields are created in the Clarify metadata:

.. code-block::

        {
            "name": "Sample Video 1",
            "created_at": "2016-01-12T17:06:39.284Z",
            "updated_at": "2016-01-29T17:44:26.340Z",
            "state": "ACTIVE",
            "description": "A sample video of a bird flying."
            "long_description": "You'll never look at a bird the same way after you've seen this video.",
            "tags": [
                "birds",
                "fly",
                "sky"
            ]
        }

The state field corresponds to the Video's state (``ACTIVE`` or ``INACTIVE``) in Brightcove. If you use this flag, you can limit Clarify searches to only active videos by using a ``filter`` on the ``state`` field in your search request. See http://clarify.io/blog/searching-audio-and-video-metadata-with-clarify/ for more information.


Limitations
------------

Syncing
^^^^^^^

In order to keep things simple and allow the script to work without Brightcove API write access, when the script starts it fetches the all the video metadata from the Brightcove library and all the bundle data from Clarify. It then compares these to know what needs updating. This has several implications:

* If the video library is too large, the sync will be slow and may lead to timeouts. It should be fine for libraries up to several thousand videos.
* If the Video metadata is updated frequently in Brightcove, this will cause the bundle metadata to also be updated frequently.
* Videos should not be deleted from Brightcove during a sync. Due to pagination in the Brightcove API, deleting a video may result in a still existing video to not be fetched and the sync tool will think the corresponding Clarify bundle should be deteled. Note that the sync tool will always prompt you before deleting a bundle. Creation of new videos and updates to videos are fine to do during a sync but they will not get picked up until the next sync is run.

To overcome the above limitations, the script could be improved by using the Brightcove API in write mode. Each Video could have a ``custom_field`` containing the bundle href/id of the Video's corresponding bundle in Clarify. Then the Brightcove API could be used to search for the Videos that need changing, for example videos with no bundle href/id set.

The iteration/pagination issue could be resolved by refetching the video library until the video count matches the expected count.

Video Media
^^^^^^^^^^^^^

The Clarify API ingests media from URLs. This sync tool looks in the Sources (renditions) of a Brightcove Video to find one with the highest resolution (up to 1080p), encoded using the H264 codec, and featuring an http/https Src URL. If no suitable video URL is found, the bundle will not be created in Clarify. Currently, the tool only supports videos that were ingested with Brightcove and does not support "remote" videos.

Support for remote videos could be easily added. If the ``remote`` field in the Video Source is ``true``, the Brightcove CMS Asset API can be used to get the Rendition list, and from that the ``remote_url`` of the desired rendition. This URL can be used for the Clarify bundle.

Custom Fields
^^^^^^^^^^^^^

Currently the custom fields are not used in the Clarify metadata. An improvement to this script would allow you to specify a list of custom fields that would be mapped to bundle metadata fields.


History (Change Log)
--------------------

See `HISTORY.rst <HISTORY.rst>`_


LICENSE
-------

See `LICENSE <LICENSE>`_


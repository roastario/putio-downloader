#!/usr/bin/python
import datetime

__author__ = 'stefanofranz'
# -*- coding: utf-8 -*-
import os
import json
import logging

import requests.requests.sessions as requests
import dateutil.dateutil.parser as date_parser

import threaded_downloader as td
import download_record_keeper as rk


BASE_URL = 'https://api.put.io/v2'
logger = logging.getLogger(__name__)


class Client(object):
    def __init__(self, access_token, record_keeper=None):
        self.record_keeper = record_keeper if record_keeper is not None else rk.YES_MAN
        self.access_token = access_token
        self.session = requests.session()

        # Keep resource classes as attributes of client.
        # Pass client to resource classes so resource object
        # can use the client.
        attributes = {'client': self}
        self.File = type('File', (_File,), attributes)
        self.Transfer = type('Transfer', (_Transfer,), attributes)
        self.Account = type('Account', (_Account,), attributes)

    def request(self, path, method='GET', params=None, data=None, files=None,
                headers=None, raw=False, stream=False):
        """
        Wrapper around requests.request()

        Prepends BASE_URL to path.
        Inserts oauth_token to query params.
        Parses response as JSON and returns it.

        """
        if not params:
            params = {}

        if not headers:
            headers = {}

        # All requests must include oauth_token
        params['oauth_token'] = self.access_token

        headers['Accept'] = 'application/json'

        url = BASE_URL + path
        logger.debug('url: %s', url)

        response = self.session.request(
            method, url, params=params, data=data, files=files,
            headers=headers, allow_redirects=True, stream=stream)
        logger.debug('response: %s', response)
        if raw:
            return response

        logger.debug('content: %s', response.content)
        try:
            response = json.loads(response.content)
        except ValueError:
            raise Exception('Server didn\'t send valid JSON:\n%s\n%s' % (
                response, response.content))

        if response['status'] == 'ERROR':
            raise Exception(response['error_type'])

        return response


class _BaseResource(object):
    client = None

    def __init__(self, resource_dict):
        """Constructs the object from a dict."""
        # All resources must have id and name attributes
        self.id = None
        self.name = None
        self.__dict__.update(resource_dict)
        self.name = self.name.encode('utf-8')
        try:
            self.created_at = date_parser.parse(self.created_at)
            self.age = (datetime.datetime.today() - self.created_at).days
        except (AttributeError, ValueError):
            self.created_at = None

    def __str__(self):
        return self.name.encode('utf-8')

    def __repr__(self):
        # shorten name for display
        name = self.name[:17] + '...' if len(self.name) > 20 else self.name
        return '<%s id=%r, name="%r">' % (
            self.__class__.__name__, self.id, name)


class _File(_BaseResource):
    @classmethod
    def get(cls, id):
        d = cls.client.request('/files/%i' % id, method='GET')
        t = d['file']
        return cls(t)

    @classmethod
    def list(cls, parent_id=0):
        d = cls.client.request('/files/list', params={'parent_id': parent_id})
        files = d['files']
        return [cls(f) for f in files]

    @classmethod
    def upload(cls, path, name=None, parent_id=0):
        with open(path) as f:
            if name:
                files = {'file': (name, f)}
            else:
                files = {'file': f}
            d = cls.client.request('/files/upload', method='POST',
                                   data={'parent_id': parent_id}, files=files)
        f = d['file']
        return cls(f)

    def dir(self):
        """List the files under directory."""
        return self.list(parent_id=self.id)

    def download(self, dest='.', delete_after_download=False, number_of_connections=1, days_to_keep=7):
        if self.content_type == 'application/x-directory':
            self._download_directory(dest, delete_after_download, number_of_connections=number_of_connections,
                                     days_to_keep=days_to_keep)
        else:
            self._download_file(dest, delete_after_download, number_of_connections=number_of_connections,
                                days_to_keep=days_to_keep)

    def _download_directory(self, dest='.', delete_after_download=False, number_of_connections=1, days_to_keep=7):
        name = self.name
        if isinstance(name, unicode):
            name = name.encode('utf-8', 'replace')

        dest = os.path.join(dest, name)
        if not os.path.exists(dest):
            os.mkdir(dest)

        for sub_file in self.dir():
            sub_file.download(dest, delete_after_download, number_of_connections=number_of_connections, days_to_keep=days_to_keep)

        if delete_after_download and self.age > days_to_keep:
            print "Deleting folder {0} as it more than {1} days old".format(self.name, days_to_keep)
            self.delete()

    def _download_file(self, dest='.', delete_after_download=False, number_of_connections=1, days_to_keep=7):
        print "Attempting to download", self.name

        if self.client.record_keeper.should_download(os.path.join(dest, self.name)):
            try:
                downloader = td.ThreadedDownloader(".", number_of_connections)
                url = BASE_URL + '/files/' + str(self.id) + '/download?oauth_token=' + self.client.access_token
                downloader.multi_part_download_file(dest, url, file_info=self)
                self.client.record_keeper.record_completion(os.path.join(dest, self.name))
            except Exception, e:
                print "Failed to download " + self.name + " due to " + str(e)
            
        else:
            print "Skipping: " + self.name + " as it has been downloaded already!"

        if delete_after_download and self.age > days_to_keep:
            print "Deleting folder {0} as it more than {1} days old".format(self.name, days_to_keep)
            self.delete()
        else:
            print "Leaving {0} on put.io as it is less than {1} days old".format(self.name, days_to_keep)

    def delete(self):
        return self.client.request('/files/delete', method='POST',
                                   data={'file_ids': str(self.id)})

    def move(self, parent_id):
        return self.client.request('/files/move', method='POST',
                                   data={'file_ids': str(self.id), 'parent_id': str(parent_id)})

    def rename(self, name):
        return self.client.request('/files/rename', method='POST',
                                   data={'file_id': str(self.id), 'name': str(name)})


class _Transfer(_BaseResource):
    @classmethod
    def list(cls):
        d = cls.client.request('/transfers/list')
        transfers = d['transfers']
        return [cls(t) for t in transfers]

    @classmethod
    def get(cls, id):
        d = cls.client.request('/transfers/%i' % id, method='GET')
        t = d['transfer']
        return cls(t)

    @classmethod
    def add_url(cls, url, parent_id=0, extract=False, callback_url=None):
        d = cls.client.request('/transfers/add', method='POST', data=dict(
            url=url, save_parent_id=parent_id, extract=extract,
            callback_url=callback_url))
        t = d['transfer']
        return cls(t)

    @classmethod
    def add_torrent(cls, path, parent_id=0, extract=False, callback_url=None):
        with open(path) as f:
            files = {'file': f}
            d = cls.client.request('/files/upload', method='POST', files=files,
                                   data=dict(save_parent_id=parent_id,
                                             extract=extract,
                                             callback_url=callback_url))
        t = d['transfer']
        return cls(t)

    @classmethod
    def clean(cls):
        return cls.client.request('/transfers/clean', method='POST')


class _Account(_BaseResource):
    @classmethod
    def info(cls):
        return cls.client.request('/account/info', method='GET')

    @classmethod
    def settings(cls):
        return cls.client.request('/account/settings', method='GET')


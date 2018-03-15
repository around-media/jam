import pytest
from googleapiclient.http import HttpMockSequence
import json
import six
import httplib2
import io


class HttpMockIterableSequence(HttpMockSequence):
    """Gives two improvements over :class:`googleapiclient.http.HttpMockSequence`:

        * Accepts now iterators. Useful to avoid loading all resources at once.
        * The content of the response now accepts the following extra value:
            `file:a/b/c/myfile.ext` => The response will be read from `a/b/c/myfile.ext`

    """
    def __init__(self, iterable):
        super(HttpMockIterableSequence, self).__init__(
            iterable if isinstance(iterable, six.Iterator) else iter(iterable),
        )

    def request(self, uri,
              method='GET',
              body=None,
              headers=None,
              redirections=1,
              connection_type=None):
        resp, content = self._iterable.next()
        if content == 'echo_request_headers':
            content = headers
        elif content == 'echo_request_headers_as_json':
            content = json.dumps(headers)
        elif content == 'echo_request_body':
            if hasattr(body, 'read'):
                content = body.read()
            else:
                content = body
        elif content == 'echo_request_uri':
            content = uri
        if isinstance(content, six.string_types):
            if isinstance(content, six.text_type):
                content = content.encode('utf-8')
            if content.startswith('file:'):
                with open(content[len('file:'):], 'r') as f:
                    content = f.read()
        return httplib2.Response(resp), content


@pytest.fixture
def http_sequence_factory():
    return HttpMockIterableSequence

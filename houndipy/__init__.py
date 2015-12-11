import time
import hmac
import json
from uuid import uuid4
from base64 import urlsafe_b64decode, urlsafe_b64encode

from requests import Session
from requests.adapters import HTTPAdapter


from request_info import validate_request_info


class HoundifyAdapter(HTTPAdapter):

    def __init__(self, client_id, client_key):
        self.user_id = uuid4().hex
        self.client_id = client_id
        self.client_key = client_key

        super().__init__()

    def send(self, request, **kwargs):
        request = self.sign_request(request)

        # houndify doesn't accept + in place of space charactors
        request.url = request.url.replace('+', '%20')

        # we have to translate between what requests uses, and what houdify
        # uses. i don't understand why Houndify uses non-standard headers
        if 'Accept-Encoding' in request.headers:
            request.headers['Hound-Response-Accept-Encoding'] = (
                request.headers['Accept-Encoding']
            )

        response = super().send(request, **kwargs)

        if 'Hound-Response-Content-Encoding' in response.headers:
            # this doesn't work unless we set it on the raw response,
            # not sure why
            response.raw.headers['Content-Encoding'] = (
                response.headers.pop('Hound-Response-Content-Encoding')
            )

        return response

    def sign_request(self, request):
        headers = self._sign_request(
            request_id=uuid4().hex,
            timestamp=int(time.time()),
            user_id=self.user_id,
            client_id=self.client_id,
            client_key=self.client_key
        )

        request = request.copy()
        request.headers.update(headers)
        return request

    def _sign_request(self, request_id, timestamp, user_id, client_id,
                      client_key):
        '''
        Performs the actual signing of the request.

        Although not mentioned in the Houndify documentation to the best
        of my knowledge, the urlsafe version of base64 is required here,
        along with the sha256 version of HMAC (also left unmentioned).
        '''
        value = '{};{}{}'.format(user_id, request_id, timestamp)
        clientKeyBuffer = urlsafe_b64decode(client_key)
        q_hmac = hmac.HMAC(
            clientKeyBuffer,
            value.encode('utf8'),
            digestmod='sha256'
        )
        digest = q_hmac.digest()
        signature = urlsafe_b64encode(digest).decode()

        return {
            'Hound-Request-Authentication': '{};{}'.format(
                user_id, request_id
            ),
            'Hound-Client-Authentication': '{};{};{}'.format(
                client_id, timestamp, signature
            )
        }


class Conversation:
    def __init__(self, client):
        self.client = client
        self.converstation_state = None

    def text(self, *args, **kwargs):
        kwargs.setdefault('ConversationState', self.converstation_state or {})
        res = self.client.text(*args, **kwargs)
        data = res.json()
        if 'AllResults' in data:
            self.converstation_state = (
                data['AllResults'][0]['ConversationState']
            )
        return res

    def speech(self, *args, **kwargs):
        kwargs.setdefault('ConversationState', self.converstation_state or {})
        res = self.client.text(*args, **kwargs)
        self.converstation_state = (
            res.json()['AllResults'][0]['ConversationState']
        )
        return res


class Client:

    def __init__(self, client_id, client_key):
        self._sess = Session()
        self._sess.mount('https://', HoundifyAdapter(client_id, client_key))

    def converse(self):
        return Conversation(self)

    def _request(self, url, request_info, **kwargs):
        res = self._sess.post(
            url,
            headers={
                'Hound-Request-Info': json.dumps(
                    validate_request_info(request_info)
                )
            },
            **kwargs
        )
        data = res.json()
        if 'ErrorMessage' in data:
            raise HoundipyException(data['ErrorMessage'])
        return res

    def text(self, query, **kwargs):
        return self._request(
            'https://api.houndify.com/v1/text',
            params={'query': query},
            request_info=kwargs
        )

    def speech(self, audio, **kwargs):
        return self._request(
            'https://api.houndify.com/v1/audio',
            data=audio,
            request_info=kwargs
        )


class HoundipyException(Exception):
    pass

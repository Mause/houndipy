import time
import hmac
import json
from uuid import uuid4
from base64 import urlsafe_b64decode, urlsafe_b64encode

from requests import Session
from requests.adapters import HTTPAdapter




class HoundifyAdapter(HTTPAdapter):

    def __init__(self, client_id, client_key):
        self.user_id = uuid4().hex
        self.client_id = client_id
        self.client_key = client_key

        super().__init__()

    def send(self, request, **kwargs):
        self.sign_request(request)

        if 'Accept-Encoding' in request.headers:
            request.headers['Hound-Response-Accept-Encoding'] = (
                request.headers['Accept-Encoding']
            )

        response = super().send(request, **kwargs)

        # why does Houndify use non-standard headers?!
        if 'Hound-Response-Content-Encoding' in response.headers:
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

        request.headers.update(headers)

    def _sign_request(self, request_id, timestamp, user_id, client_id,
                      client_key):
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

    def text(self, query, **kwargs):
        return self._sess.post(
            'https://api.houndify.com/v1/text',
            params={'query': query},
            headers={'Hound-Request-Info': json.dumps(kwargs)}
        )

    def speech(self, audio, **kwargs):
        return self._sess.post(
            'https://api.houndify.com/v1/audio',
            data=audio,
            headers={'Hound-Request-Info': json.dumps(kwargs)}
        )

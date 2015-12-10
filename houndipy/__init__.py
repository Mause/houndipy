import time
import hmac
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
        return super().send(request, **kwargs)

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


class Client:

    def __init__(self, client_id, client_key):
        self._sess = Session()
        self._sess.mount('https://', HoundifyAdapter(client_id, client_key))

    def text(self, query):
        return self._sess.post(
            'https://api.houndify.com/v1/text',
            params={'query': query}
        )

    def speech(self, audio):
        return self._sess.post(
            'https://api.houndify.com/v1/audio',
            data=audio
        )

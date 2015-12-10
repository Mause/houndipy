import time
import json
import hmac
import unittest
from io import BytesIO
from uuid import uuid4
from base64 import urlsafe_b64decode, urlsafe_b64encode
from contextlib import closing

import wave
import pyaudio
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


class TestClient(unittest.TestCase):
    def test_headers(self):
        res = HoundifyAdapter._sign_request(
            None,
            user_id='ae06fcd3-6447-4356-afaa-813aa4f2ba41',
            request_id='70aa7c25-c74f-48be-8ca8-cbf73627c05f',
            timestamp=1418068667,
            client_id='KFvH6Rpy3tUimL-pCUFpPg==',
            client_key='KgMLuq-k1oCUv5bzTlKAJf_mGo0T07jTogbi6apcqLa114CCPH3rlK4c0RktY30xLEQ49MZ-C2bMyFOVQO4PyA==',
        )

        SHOULD = {
            'Hound-Request-Authentication': 'ae06fcd3-6447-4356-afaa-813aa4f2ba41;70aa7c25-c74f-48be-8ca8-cbf73627c05f',
            'Hound-Client-Authentication': 'KFvH6Rpy3tUimL-pCUFpPg==;1418068667;myWdEfHJ7AV8OP23v8pCH1PILL_gxH4uDOAXMi06akk='
        }

        self.assertEqual(res, SHOULD)


class SendStream:
    def __init__(self, stream, rate, chunk_size, seconds):
        self.chunk_size = chunk_size
        self.seconds = seconds
        self.stream = stream
        self.rate = rate

    def __iter__(self):
        return iter(self.gen())

    def gen(self):
        print('starting')
        for i in range(0, int(self.rate / self.chunk_size * self.seconds)):
            yield self.stream.read(self.chunk_size)
        print('stopping')


def get_recording(seconds):
    CHUNK = 1024
    WIDTH = 2
    CHANNELS = 1
    RATE = 16000

    p = pyaudio.PyAudio()
    FORMAT = p.get_format_from_width(WIDTH)
    with closing(p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)) as stream:

        print("* recording")
        frames = [
            stream.read(CHUNK)
            for _ in range(0, int(RATE / CHUNK * seconds))
        ]
        print("* done recording")

    p.terminate()

    file = BytesIO()
    with wave.open(file, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    return file.getvalue()


def main():
    with open('auth.json') as fh:
        auth = json.load(fh)
    client = Client(
        auth['client_id'],
        auth['client_key']
    )

    # r = client.text('how old is chad reed')
    data = get_recording(seconds=5)
    print('sending')
    r = client.speech(data)
    print('sent')

    if not r.ok:
        print(r.text)

    r.raise_for_status()

    res = r.json()

    try:
        for sres in res['AllResults']:
            print(sres['NativeData']['LongResult'])
    except KeyError:
        from pprint import pprint
        pprint(res)

if __name__ == '__main__':
    main()

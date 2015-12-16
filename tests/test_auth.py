import unittest
from houndipy import sign_request


class TestClient(unittest.TestCase):

    def test_headers(self):
        # this is example data from the documentation
        res = sign_request(
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

if __name__ == '__main__':
    unittest.main()

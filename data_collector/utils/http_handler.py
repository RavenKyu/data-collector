import requests
import logging

logger = logging.getLogger(__name__)

################################################################################
class CommunicationHTTP:
    # ==========================================================================
    def __init__(self, host, port, endpoint=''):
        self.host = host
        self.port = port
        if endpoint:
            endpoint += '/'
        self.url = f'http://{self.host}:{self.port}/{endpoint}'

    # ==========================================================================
    def result(self, response):
        if not response.ok:
            logger.error(f'code: {response.status_code} '
                              f'message:{response.reason}')
            return response.ok, None, response.reason

        logger.debug(f'code: {response.status_code}, url: {response.url}')
        return response.ok, response.text, response.reason

    # ==========================================================================
    def get(self, api, *args, **kwargs):
        with requests.Session() as s:
            response = s.get(self.url + api, **kwargs)
        return self.result(response)

    # ==========================================================================
    def set(self, method='post', api='', *args, **kwargs):
        with requests.Session() as s:
            response = s.post(self.url + api, json=kwargs['json_data'])
        self.result(response)

    # ==========================================================================
    def remove(self, *args, **kwargs):
        pass
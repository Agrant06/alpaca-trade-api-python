import dateutil.parser
import os
import re
import requests
from requests.exceptions import HTTPError

ISO8601YMD = re.compile(r'\d{4}-\d{2}-\d{2}T')


class APIError(Exception):
    def __init__(self, error):
        super().__init__(error['message'])
        self._error = error

    @property
    def code(self):
        return self._error['code']


class API(object):
    def __init__(self, api_key):
        self._key = api_key
        self._base_url = os.environ.get(
            'ALPACA_API_BASE_URL', 'https://api.alpaca.markets')
        self._session = requests.Session()

    def _request(self, method, path, data=None):
        url = self._base_url + path
        headers = {
            'X-API-KEY': self._key,
        }
        opts = {
            'headers': headers,
        }
        if method.upper() == 'GET':
            opts['params'] = data
        else:
            opts['json'] = data
        resp = self._session.request(method, url, **opts)
        try:
            resp.raise_for_status()
        except HTTPError as exc:
            error = resp.json()
            if 'code' in error:
                raise APIError(error)
        return resp.json()

    def get(self, path, data=None):
        return self._request('GET', path, data)

    def post(self, path, data=None):
        return self._request('POST', path, data)

    def patch(self, path, data=None):
        return self._request('PATCH', path, data)

    def delete(self, path, data=None):
        return self._request('DELETE', path, data)

    def list_accounts(self):
        '''Get a list of accounts'''
        resp = self._request('GET', '/api/v1/accounts')
        return [Account(o, self) for o in resp]


class Entity(object):
    def __init__(self, obj):
        self._obj = obj

    def __getattr__(self, key):
        if key in self._obj:
            val = self._obj[key]
            if key.endswith('_at') and ISO8601YMD.match(val):
                return dateutil.parser.parse(val)
            else:
                return val
        return getattr(super(), key)


class Account(Entity):

    def __init__(self, obj, api):
        super().__init__(obj)
        self._api = api
        self._account_id = obj['id']

    def _fullpath(self, path, v='1'):
        return '/api/v{}/accounts/{}{}'.format(v, self._account_id, path)

    def get(self, path, data=None):
        fullpath = self._fullpath(path)
        return self._api.get(fullpath, data)

    def post(self, path, data=None):
        fullpath = self._fullpath(path)
        return self._api.post(fullpath, data)

    def delete(self, path, data=None):
        fullpath = self._fullpath(path)
        return self._api.delete(fullpath, data)

    def list_orders(self):
        '''Get a list of orders'''
        resp = self.get('/orders')
        return [Order(o) for o in resp]

    def create_order(self, assert_id, shares, side, type, timeinforce,
                     limit_price=None, stop_price=None, client_order_id=None):
        '''Request a new order'''
        data = dict(
            assert_id=assert_id,
            shares=shares,
            side=side,
            type=type,
            timeinforce=timeinforce,
            limit_price=limit_price,
            stop_price=stop_price,
            client_order_id=client_order_id,
        )
        resp = self.post('/orders', data)
        return Order(resp)

    def get_order(self, order_id):
        '''Get an order'''
        resp = self._api.get('/api/v1/{}/orders/{}'.format(
            self._account_id, order_id,
        ))
        return Order(resp)

    def get_order_by_client_order_id(self, client_order_id):
        '''Get an order by client order id'''
        resp = self.get('/orders', data={
            'client_order_id': client_order_id,
        },
        )
        return Order(resp)

    def delete_order(self, order_id):
        '''Cancel an order'''
        self.delete('/orders/{}'.format(order_id))

    def list_positions(self):
        '''Get a list of open positions'''
        resp = self.get('/positions')
        return [Position(o) for o in resp]

    def get_position(self, asset_id):
        '''Get an open position'''
        resp = self.get('/positions/{}'.format(asset_id))
        return Position(resp)


class Order(Entity):
    pass


class Position(Entity):
    pass

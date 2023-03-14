#!/usr/bin/env python3
# client.py

# internal imports
import logging
import re
from datetime import datetime, timedelta

# external imports
import requests
import mechanicalsoup


class OperlogClient:
    """Operlog Client Class"""

    def __init__(self, url: str, username: str, password: str,
                 token_file: str = '.token'):
        self.url = url
        self.username = username
        self.password = password
        self.token_file = token_file
        # get token from file
        try:
            with open(self.token_file, 'r') as f:
                token = f.read()
        except FileNotFoundError:
            token = update_token()
        if token is not None:
            self.token = token
        else:
            raise RuntimeError('Failed to get token')

    def update_token(self):
        """Update token ans save it to file"""
        creds = {'username': self.username, 'password': self.password}
        r = requests.post(f'{self.url}/loginapi', json=creds)
        try:
            token = r.json()['access_token']
        except Exception as e:
            logging.error(f'Get new token failed: {e}')
            return None
        with open(self.token_file, 'w') as f:
            f.write(token)
        return token

    def api_call(self, endpoint: str, method: str, data: dict = None):
        """Send request to api"""
        args = [self.url + endpoint]
        # try 2 times msximum (second try if token is expired)
        for i in range(2):
            kwargs = {'headers': {"Authorization": f"Bearer {self.token}"},
                      'json': data}
            try:
                r = eval(f'requests.{method}(*args, **kwargs)')
            except Exception as e:
                logging.error(f'API call error: {e}')
                return None
            if r.status_code == 401:
                # token expired - update
                token = self.update_token()
                if token is not None:
                    self.token = token
            else:
                break
        if r.status_code == 401:
            logging.error('Authorization failed')
            return None
        return r

    def get_all_items(self):
        """Get all items"""
        res = self.api_call('/api', 'get')
        if res.status_code != 200:
            return res.status_code
        res = res.json()
        return res

    def add_item(self, msg: str, msg2: str = None):
        """Add new item"""
        data = {'event': msg}
        if msg2 is not None:
            data.update({'after_event': msg2})
        res = self.api_call(f'/api', 'post', data=data)
        if res.status_code != 201:
            return res.status_code
        res = res.json()
        return res

    def get_item(self, id: int):
        """Get item by id"""
        res = self.api_call(f'/api/{id}', 'get')
        if res.status_code != 200:
            return res.status_code
        res = res.json()
        return res

    def edit_item(self, id: int, data: dict):
        """Edit item by id"""
        res = self.api_call(f'/api/{id}', 'put', data=data)
        if res.status_code != 201:
            return res.status_code
        res = res.json()
        return res

    def delete_item(self, id: int):
        """Delete item by id"""
        res = self.api_call(f'/api/{id}', 'delete')
        return res.status_code

    def search(self, pattern: str):
        """Search in items"""
        res = {}
        rgx = rf'(?i)({pattern})'
        # red color for highlighting
        rgx_color = r'\033[31m\1\033[0m'
        items = self.get_all_items()
        for item_id, item in items.items():
            if re.search(rgx, item['event']+item['after_event']):
                colored = item
                for i in ['event', 'after_event']:
                    colored[i] = re.sub(rgx, rgx_color, item[i])
                    res[item_id] = colored
        return res


class OperlogParser:
    """Parser for non-api web interface"""

    def __init__(self, url: str):
        self.url = url
        self.browser = mechanicalsoup.StatefulBrowser(
            user_agent='operlog/0.1')

    def get_items_in_range(self, start: int = 0, end: int = 0):
        """Get items between two timestamps"""

        # set default end time as now
        if end == 0:
            end = int(datetime.timestamp(datetime.now()))

        keys = ['timestamp', 'event', 'specialist',
                'end_time', 'comment', 'operator']
        res = []
        # convert timestamps to text date
        date1 = datetime.fromtimestamp(start).strftime('%Y-%m-%d')
        date2 = datetime.fromtimestamp(end).strftime('%Y-%m-%d')
        page = self.browser.post(self.url+'/search', data={
            'date1': date1, 'date2': date2, 'event': ''})
        header = page.soup.find(class_='table_oper_log').find('tr')
        rows = header.find_all_next('tr')
        for row in rows:
            vals = list(map(lambda x: x.text.strip(), row.find_all('td')))
            data = dict(zip(keys, vals))
            # convert date from text to unixtime
            data['timestamp'] = int(datetime.timestamp(datetime.strptime(
                data['timestamp'], '%Y-%m-%d %H:%M:%S')))
            # check time range
            if data['timestamp'] < start or data['timestamp'] > end:
                continue
            # clear empty values
            if data['specialist'] == '-----':
                data['specialist'] = None
            if data['end_time'] == 'None':
                data['end_time'] = None
            res.append(data)
        return res

#!/usr/bin/env python3
# cli.py

# internal imports
import os

# external imports
import click
from datetime import datetime
import yaml

# local imports
from operlog_client.client import OperlogClient

# change working dir to current
os.chdir(os.path.dirname(os.path.realpath(__file__)))

# load config from file
with open('config.yml', 'r') as file:
    cfg = yaml.safe_load(file)

# init client
operlog = OperlogClient(cfg['base_url'], cfg['username'], cfg['password'])


def fmt_item(item: dict, item_id: int = None):
    """Format event item"""
    # skip if item is error code
    if type(item) != dict:
        return item
    # add item id if needed
    if 'id' not in item:
        item['id'] = item_id
    # convert time format if needed
    try:
        item['time_event'] = datetime.strptime(
            item['time_event'],
            '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M')
    except Exception:
        pass
    # remove leading space from second message
    item['after_event'] = item['after_event'].strip()
    res = (f"[{item['time_event']} - {item['time_report']}] "
           f"{item['operator']} --> {item['username_report']} "
           f"[{item['id']}]\n{'='*80}\n{item['event']}\n")
    if item['after_event'] != '':
        res += f"{'-'*80}\n{item['after_event']}\n"
    res += '='*80 + '\n'
    return res


@click.group()
def cli():
    pass


@cli.command()
@click.argument('msg')
@click.argument('msg2', required=False)
@click.option('--silent', '-s', is_flag=True, help='Suppress stdout.')
def add(msg: str, msg2: str, silent: bool):
    """Add event to log"""
    res = operlog.add_item(msg, msg2)
    if not silent:
        print(fmt_item(res))


@cli.command()
@click.argument('id')
def delete(id: int):
    """Delete event from log"""
    res = operlog.delete_item(id)
    print(res)


@cli.command()
@click.argument('id')
def get(id: int):
    """Show event by id"""
    res = operlog.get_item(id)
    print(fmt_item(res))


@cli.command()
@click.argument('pattern')
def search(pattern: str):
    """Search event by pattern"""
    res = operlog.search(pattern)
    for item_id, item in res.items():
        print(fmt_item(item, item_id))


if __name__ == '__main__':
    cli()

#!/usr/bin/env python3
import requests
import json
import yaml
import sys
import argparse
import tempfile
import os
import hashlib
from subprocess import call

config = os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yml")

# Read configuration
with open(config, 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)


# Functions
def call_api(method, url, object_data=None):
    headers = { 'Content-Type': 'application/json',
                'Accept': 'application/json' }
    response = requests.request(method, url, json=object_data, headers=headers,
                                params=cfg['params'])
    if not response.text:
        print("No response received (error %i)" % response.status_code)
        sys.exit(1)

    json_response=json.loads(response.text)

    if "errormessages" in json_response:
        for err in json_response['errormessages']['errormessage']:
            if 'args' in err:
                print(err['text'].replace('\n', ' ').replace('\r', '') \
                    % tuple([d['value'] for d in err['args']]))
            else:
                print(err['text'])

    return json_response


# Print formatted output from JSON
def print_output(json, object_file):
    if "objects" in json:
        for attr in json['objects']['object'][0]['attributes']['attribute']:
            object_file.write("%-20s %s\n" % (attr['name']+':',
                                              attr['value']))
    if object_file:
        object_file.close()


def read_input(object_file):
    attr = []
    for line in object_file.readlines():
        if not line: continue
        attr.append({'name':line.split(':', 1)[0].strip(),
                     'value':line.split(':', 1)[1].strip() })

    object_data = {
        "objects": {
            "object": [
                {
                    "attributes": {
                         "attribute": attr
                    }
                }
            ]
        }
    }
    return object_data


# Get record
def get(args):
    print("Getting %s object %s" % (args.type, args.key))
    url = '/'.join((cfg['base_url'],args.type,args.key))
    json_response=call_api("GET", url)
    print_output(json_response, args.file)
    return


# Delete record
def delete(args):
    print("Deleting %s object %s" % (args.type, args.key))
    url = '/'.join((cfg['base_url'],args.type,args.key))
    json_response=call_api("DELETE", url)
    return


# Create record
def create(args):
    print("Creating %s object" % (args.type))
    url = '/'.join((cfg['base_url'],args.type))
    object_data = read_input(args.file)
    json_response=call_api("POST", url, object_data)
    print_output(json_response, sys.stdout)
    return


# Update record
def update(args):
    print("Updating %s object %s" % (args.type, args.key))
    url = '/'.join((cfg['base_url'],args.type,args.key))
    object_data = read_input(args.file)
    json_response=call_api("PUT", url, object_data)
    print_output(json_response, sys.stdout)
    return


# Edit record
def edit(args):
    tmp_fd, tmp_name = tempfile.mkstemp()
    get(parser.parse_args(["get", args.type, args.key, tmp_name]))
    EDITOR = os.environ.get('EDITOR','vim')
    # Memory inefficient, but who cares?
    hash1 = hashlib.md5(open(tmp_name).read().encode('utf-8')).hexdigest()
    call([EDITOR, tmp_name])
    hash2 = hashlib.md5(open(tmp_name).read().encode('utf-8')).hexdigest()

    if hash1 != hash2:
        update(parser.parse_args(["update", args.type, args.key, tmp_name]))
    else:
        print("Object unchanged, not updating")

    os.unlink(tmp_name)
    return


# Arguments parsing
# USAGE : ./ripe-api.py delete <TYPE> <KEY>
#         ./ripe-api.py create <TYPE> <FILE>
#         ./ripe-api.py update <TYPE> <KEY> <FILE>
#         ./ripe-api.py get <TYPE> <KEY> <FILE>
#         ./ripe-api.py edit <TYPE> <KEY>
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='Action to perform',dest='action')

parser_get = subparsers.add_parser('get', help='Get an object')
parser_get.add_argument('type', type=str, help='Object type')
parser_get.add_argument('key', type=str, help='Object identifier')
parser_get.add_argument('file', type=argparse.FileType('w'), help='Output file')

parser_delete = subparsers.add_parser('delete', help='Delete an object')
parser_delete.add_argument('type', type=str, help='Object type')
parser_delete.add_argument('key', type=str, help='Object identifier')

parser_post = subparsers.add_parser('create', help='Create an object')
parser_post.add_argument('type', type=str, help='Object type')
parser_post.add_argument('file', type=argparse.FileType('r'), help='Input file')

parser_put = subparsers.add_parser('update', help='Update an object')
parser_put.add_argument('type', type=str, help='Object type')
parser_put.add_argument('key', type=str, help='Object identifier')
parser_put.add_argument('file', type=argparse.FileType('r'), help='Input file')

parser_edit = subparsers.add_parser('edit', help='Edit an object')
parser_edit.add_argument('type', type=str, help='Object type')
parser_edit.add_argument('key', type=str, help='Object identifier')

args = parser.parse_args()
globals()[args.action](args)

import os
import time
import json 
import shutil
import argparse
import datetime

from dateutil import parser



def parse_args():
  parser = argparse.ArgumentParser(description='Sanitize the Docker registry dataset and group them by users')
  parser.add_argument('-i', '--input', type=str, dest='input', default='../../data/data_centers', 
                      help='Base directory of the input datasets')
  parser.add_argument('-o', '--output', type=str, dest='output', default='../../data/clean_data', 
                      help='Base directory of the output datasets')
  parser.add_argument('-d', '--data-center', type=str, dest='data_center', default='dev-mon01',
                      help='Data center of the dataset')
  return parser.parse_args()


def select_and_group(args):
  in_dir, out_dir, data_center = args.input, args.output, args.data_center
  events = {} 
  start_time = time.time()
  for fn in os.listdir('%s/%s'%(in_dir, data_center)):
    with open('%s/%s/%s'%(in_dir, data_center, fn), 'r') as f:
      for e in json.load(f):
        method, uri, cli = e['http.request.method'], e['http.request.uri'], e['http.request.remoteaddr']
        if method != 'GET' or len(uri.split('/')) < 2:
          continue
        event = {
          'timestamp': datetime.datetime.fromtimestamp(parser.parse(e['timestamp']).timestamp() - e['http.request.duration']), 
          'host': e['host'],
          'uri': e['http.request.uri'], 
          'status': e['http.response.status'],
          'size': e['http.response.written'],
        }
        events.setdefault(cli, []).append(event)
  out_dir = '%s/%s'%(out_dir, data_center)
  if os.path.exists(out_dir):
    shutil.rmtree(out_dir)
  os.makedirs(out_dir, exist_ok=True)
  for k in dict(events):
    print('Processing %s'%k)
    print('Sorting ...')  
    events[k] = sorted(events[k], key=lambda e: e['timestamp'])
    print('Formatting timestamps ...')
    for e in events[k]:
      e['timestamp'] = e['timestamp'].isoformat()
    print('Saving ...\n')
    with open('%s/%s.json'%(out_dir, k), 'w') as f:
      json.dump(events[k], f, indent=4)
  time_elapsed = time.time() - start_time
  print('Total clients: %d (%.3f seconds)'%(len(events), time_elapsed))


if __name__ == '__main__':
  args = parse_args()
  select_and_group(args)
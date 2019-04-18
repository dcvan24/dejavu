import os

from typing import Tuple
from google.protobuf.timestamp_pb2 import Timestamp 


def size(nbytes: int) -> str:
  if nbytes < 2 ** 10:
    return '%d B'%nbytes
  if 2 ** 10 <= nbytes < 2 ** 20:
    return '%.2f KB'%(nbytes/2 ** 10)
  if 2 ** 20 <= nbytes < 2 ** 30:
    return '%.2f MB'%(nbytes/2 ** 20)
  if 2 ** 30 <= nbytes < 2 ** 40:
    return '%.2f GB'%(nbytes/2 ** 30)
  return '%.2f TB'%(nbytes/2 ** 40)


def parse_uri(uri: str) -> Tuple[str, str, str]:
  try:
    assert isinstance(uri, str)
    uri = uri.split('/')
    repo_end = uri.index('manifests') if 'manifests' in uri else uri.index('blobs')
    return '/'.join(uri[1:repo_end]), uri[repo_end], uri[-1]
  except:
    return None, None, None

def get_current_time() -> Timestamp:
  ts = Timestamp()
  ts.GetCurrentTime()
  return ts

def get_dir_size(parent: str) -> int:
  return sum(os.path.getsize(os.path.join(p, fn))
             for p, _, fns in os.walk(parent) 
             for fn in fns)
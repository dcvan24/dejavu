import os
import time
import docker 
import logging

from typing import List
from collections import OrderedDict

import util
import puller.puller_pb2 as pb2
import puller.puller_pb2_grpc as puller_grpc 
    

class Puller:

  def __init__(self):
    self.__cli = docker.APIClient()
    self.__summaries = {}

  def start_dockerd(self, cfg: pb2.Config, dockerd_path: str):
    logging.info('Killing existing dockerd ...')
    os.system('sudo killall dockerd')
    cmd = ['sudo', dockerd_path]
    if cfg.capacity > 0:
      cmd += ['--cache-capacity', util.size(cfg.capacity).lower().replace(' ', '')]
    if cfg.cache_policy:
      cmd += ['--cache-policy', cfg.cache_policy]
    if cfg.use_archive:
      cmd += ['--cache-archive']
    cmd += ['> /tmp/dockerd.log 2>&1', '&']
    logging.info('Starting new dockerd ...')
    os.system(' '.join(cmd))
    wait_time = 1
    logging.info('Wait %ds for dockerd to fully start ...'%wait_time)    
    time.sleep(wait_time)

  def pull_image(self, pull: pb2.ImagePull) -> pb2.ImagePullSummary: 
    cli, summaries = self.__cli, self.__summaries
    image = '%s/%s:%s'%(pull.registry, pull.repo, pull.tag)

    summary = pb2.ImagePullSummary(pull=pull)
    summary.start_time.GetCurrentTime()
    pulls = OrderedDict()
    for l in cli.pull(image, stream=True, decode=True):
      dgst, status = l.get('id'), l.get('status')
      if not dgst or status not in ('Pulling fs layer', 'Download complete', 'Extracting', 
                                    'Pull complete', 'Already exists'):
        continue 
      if status == 'Pulling fs layer' and dgst not in pulls:
        pulls[dgst] = pb2.LayerStat(digest=dgst, download_start=util.get_current_time())
      elif status == 'Extracting':
        cur = pulls.setdefault(dgst, pb2.LayerStat(digest=dgst))
        cur.compact_size = self._parse_size(l['progress'].split('/')[-1])
        cur.extract_start.GetCurrentTime()
      elif status == 'Download complete':
        pulls[dgst].download_end.GetCurrentTime()
      elif status == 'Pull complete':
        pulls[dgst].extract_end.GetCurrentTime()
      elif status == 'Already exists':
        pulls[dgst] = pb2.LayerStat(digest=dgst, exists=True)
    summary.end_time.GetCurrentTime()
    if len(pulls) == 0:
      s = None
      aliases = [str(image)] + ['%s/%s'%(pull.registry, a) for a in pull.aliases]
      for a in aliases:
        s = summaries.get(a)
        if s:
          break
      layers = [pb2.LayerStat(digest=l.digest, full_size=l.full_size, compact_size=l.compact_size, exists=True) 
                for l in s.layers]
      summary.layers.extend(layers)
      return summary
    summary.layers.extend(pulls.values())
    hist = self._get_image_history(image)
    for i, p in enumerate(sorted(summary.layers, key=lambda x: -x.compact_size)):
      p.full_size = hist[i]
    if image in summaries:
      compact_sizes = [l.compact_size for l in sorted(summaries[str(image)].layers, 
                                                      key=lambda x: -x.full_size)]
      for i, l in enumerate(sorted(summary.layers, key=lambda x: -x.full_size)):
        if not l.exists:
          continue
        l.compact_size = compact_sizes[i]
    summaries.setdefault(str(image), summary)
    return summary
  
  def prune_images(self):
    self.__cli.prune_images({'dangling': False})

  def _parse_size(self, size: str) -> int:
    if not size:
      return 0
    size = size.upper()
    if size.endswith('KB'):
      size = float(size[:-2]) * 2 ** 10
    elif size.endswith('MB'):
      size = float(size[:-2]) * 2 ** 20
    elif size.endswith('GB'):
      size = float(size[:-2]) * 2 ** 20
    elif size.endswith('B'):
      size = int(size[:-1])
    else:
      size = 0
    return int(size)    
  
  def _get_image_history(self, image: str) -> List[int]:
    return sorted([h['Size'] for h in self.__cli.history(image)], 
                  key=lambda x: -x)
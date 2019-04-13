import os
import shutil
import docker
import logging
import datetime
import numpy.random as rnd

from collections import OrderedDict
from typing import Iterable, List, Dict

import util


MIN_LAYER_SQUASH_SIZE = 1000 
LAYER_SQUASH_SIM_THRESHOLD = 1 - 1e-6
LAYER_CHUNK_SIZE = 2 ** 20 # 1MB

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Layer:

  def __init__(self, dgst: str, size: int, n_hits: int=0):
    self.__dgst = dgst 
    self.__size = size 
    self.__n_hits = n_hits

  @property
  def digest(self) -> str:
    return self.__dgst

  @property
  def size(self) -> int:
    return self.__size

  @property
  def n_hits(self) -> int:
    return self.__n_hits

  def hit(self, n: int=1):
    self.__n_hits += n

  def build(self, build_dir: str, density: float=.5):
    base = '%s/layer'%build_dir
    os.makedirs(base, exist_ok=True)
    layer_f = '%s/%s'%(base, self.digest)
    if os.path.exists(layer_f):
      return
    try:
      logging.debug('Creating layer %s, size: %s ...'%(self.digest, util.size(self.size)))
      with open(layer_f, 'wb') as f:
        if self.size == 0:
          return 
        size = self.size - 1
        if size > 0:
          load_size, empty_size = int(size * density), int(size * (1 - density))
          f.seek(empty_size)
          f.write(rnd.bytes(load_size))
        f.write(b'\0')
    except Exception as e:
      logging.exception('error building layer %s'%self.digest)
      raise e

  def to_json(self) -> Dict[str, object]:
    return {
      'digest': self.digest,
      'size': self.size,
      'n_hits': self.n_hits,
    }

  def __str__(self) -> str:
    return self.digest

  def __eq__(self, l) -> bool:
    return isinstance(l, Layer) and self.digest == l.digest

  def __hash__(self) -> int:
    return hash(self.digest)


class Image:

  @classmethod
  def ID(cls, repo: str, tag: str) -> str:
    return '%s:%s'%(repo, tag)

  def __init__(self, repo: str, tag: str, n_hits: int=0, layers: Iterable=[]):
    self.__repo = repo 
    self.__tag = tag
    self.__layers = OrderedDict({l.digest: l for l in layers})
    self.__n_hits = n_hits
    self.__last_event = None

  @property
  def repo(self) -> str:
    return self.__repo 

  @property
  def tag(self) -> str:
    return self.__tag

  @property
  def layers(self) -> List[Layer]:
    return list(self.__layers.values())

  @property
  def n_hits(self) -> int:
    return self.__n_hits

  @property
  def last_event(self) -> datetime.datetime:
    return self.__last_event

  def add_layer(self, dgst: str, size: int) -> Layer:
    layers = self.__layers
    if dgst in layers and layers[dgst].size < size:
      ol, nl = layers[dgst], Layer(dgst, size)
      nl.hit(ol.n_hits)
      layers[dgst] = nl
    elif dgst not in layers:
      layers[dgst] = Layer(dgst, size)
    return layers[dgst]

  def squash_layers(self):
    layers, layer_sizes = self.__layers, {}
    for l in layers.values():
      layer_sizes.setdefault(l.size, []).append(l)

    to_squash = []
    sorted_sizes = sorted(layer_sizes.items())
    for i, (size, ls) in enumerate(sorted_sizes[:-1]):
      adj_size, adj_layers = sorted_sizes[i + 1]
      if size/adj_size > LAYER_SQUASH_SIM_THRESHOLD:
        adj_layers[-1].hit(sum(l.n_hits for l in ls))
        to_squash += ls
      elif len(ls) > 1 and size > MIN_LAYER_SQUASH_SIZE:
        ls[-1].hit(sum(l.n_hits for l in ls[:-1]))
        to_squash += ls[:-1]
    for l in to_squash:
      layers.pop(l.digest)

  def update_last_event(self, ts: datetime.datetime):
    self.__last_event = ts

  def hit(self):
    self.__n_hits += 1

  def to_json(self) -> Dict[str, object]:
    return {
      'repo': self.repo,
      'tag': self.tag, 
      'layers': [l.digest for l in self.layers],
      'n_hits': self.n_hits,
    }

  def build(self, build_dir: str, registry: str=None) -> docker.models.images.Image:
    base = '%s/image'%build_dir
    layer_base = '%s/layer'%build_dir
    try:
      logging.debug("Building %s ..."%self)
      docker_cli = docker.from_env()
      dockerfile = ['FROM scratch']
      img_dir = '%s/%s'%(base, self)
      if os.path.exists(img_dir):
        shutil.rmtree(img_dir)
      os.makedirs(img_dir, exist_ok=True)
      for l in self.layers:
        logging.debug("Generating layer %s, size %s"%(l.digest, util.size(l.size)))
        l.build(build_dir)
        os.link('%s/%s'%(layer_base, l.digest), '%s/%s'%(img_dir, l.digest))
        dockerfile += 'COPY %s /%s'%(l.digest, l.digest),
      df_path = '%s/Dockerfile'%img_dir
      with open(df_path, 'w') as f:
        f.write('\n'.join(dockerfile))
      tag = '%s/%s'%(registry, str(self)) if registry else str(self)
      img, _ = docker_cli.images.build(path=img_dir, tag=tag, 
                                       dockerfile=os.path.abspath(df_path), rm=True)
      return img
    except Exception as e:
      logging.exception('error pruning image %s'%self)
      raise e

  def push(self, registry: str=None):
    try:
      docker_cli = docker.from_env()
      repo = '%s/%s'%(registry, self.repo) if registry else self.repo
      docker_cli.images.push(repo, self.tag)
    except Exception as e:
      logging.exception('error pruning image %s'%self)
      raise e
  
  def prune(self, registry: str=None):
    try:
      docker_cli = docker.from_env()
      docker_cli.images.remove('%s/%s'%(registry, str(self)) if registry else str(self))
    except Exception as e:
      logging.exception('error pruning image %s'%self)
      raise e

  def __str__(self) -> str:
    return Image.ID(self.repo, self.tag)

  def __eq__(self, i) -> bool:
    return isinstance(i, Image) and self.repo == i.repo and self.tag == i.tag 

  def __hash__(self) -> int:
    return hash((self.repo, self.tag))

  
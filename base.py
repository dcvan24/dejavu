from __future__ import annotations

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

  def __init__(self, dgst: str, size: int):
    self.__dgst = dgst 
    self.__size = size 

  @property
  def digest(self) -> str:
    return self.__dgst

  @property
  def size(self) -> int:
    return self.__size

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
      'size': self.size
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

  def __init__(self, repo: str, tag: str, parent: Image=None, aliases: Iterable[str]=[], layers: Iterable[Layer]=[]):
    self.__repo = repo 
    self.__tag = tag
    self.__parent = parent
    self.__layers = OrderedDict({l.digest: l for l in layers})
    self.__aliases = set(aliases)

  @property
  def repo(self) -> str:
    return self.__repo 

  @property
  def tag(self) -> str:
    return self.__tag

  @property
  def parent(self) -> Image:
    return self.__parent

  @property
  def aliases(self) -> List[str]:
    return list(self.__aliases)

  @property
  def layers(self) -> List[Layer]:
    return list(self.__layers.values())

  @parent.setter
  def parent(self, p: Image):
    self.__parent = p

  def add_layer(self, dgst: str, size: int) -> Layer:
    layers = self.__layers
    if (dgst in layers and layers[dgst].size < size) or dgst not in layers:
      layers[dgst] = Layer(dgst, size)
    return layers[dgst]
  
  def add_alias(self, i: Image):
    if i:
      self.__aliases.add(str(i))

  def is_child(self, p: Image) -> bool:
    if not isinstance(p, Image): 
      return False 
    if p.parent == str(self):
      return False
    p_layers = set(l.digest for l in p.layers)
    if not p_layers.issubset(self.__layers.keys()) or len(self.layers) == len(p_layers):
      return False
    return self.__parent is None or len(p.layers) > len(self.__parent.layers)
  
  def has_alias(self, i: Image) -> bool:
    if not isinstance(i, Image):
      return False 
    a_layers = set(l.digest for l in i.layers)
    return a_layers == set(self.__layers.keys())

  def squash_layers(self):
    parent = self.__parent
    if parent:
      for l in parent.layers:
        self.__layers.pop(l.digest, None)
        
    layers, layer_sizes = self.__layers, {}
    for l in layers.values():
      layer_sizes.setdefault(l.size, []).append(l)

    to_squash = []
    sorted_sizes = sorted(layer_sizes.items())
    for i, (size, ls) in enumerate(sorted_sizes[:-1]):
      adj_size, _ = sorted_sizes[i + 1]
      if size/adj_size > LAYER_SQUASH_SIM_THRESHOLD:
        to_squash += ls
      elif len(ls) > 1 and size > MIN_LAYER_SQUASH_SIZE:
        to_squash += ls[:-1]
    for l in to_squash:
      layers.pop(l.digest)

  def to_json(self) -> Dict[str, object]:
    return {
      'repo': self.repo,
      'tag': self.tag,
      'parent': self.parent and str(self.parent), 
      'aliases': self.aliases,
      'layers': [l.digest for l in self.layers],
    }

  def build(self, build_dir: str, registry: str=None) -> docker.models.images.Image:
    base = '%s/image'%build_dir
    layer_base = '%s/layer'%build_dir
    if self.parent and registry:
      base_img = '%s/%s'%(registry, self.parent)
    elif not registry:
      base_img = self.parent 
    else:
      base_img = 'scratch'
    logging.debug("Building %s ..."%self)
    docker_cli = docker.from_env()
    dockerfile = ['FROM %s'%base_img]
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
    img, _ = docker_cli.images.build(path=img_dir, tag=tag, rm=True,
                                     dockerfile=os.path.abspath(df_path))
    api = docker.APIClient()
    for a in self.aliases:
      repo, tag = a.split(':')
      if registry:
        repo = '%s/%s'%(registry, repo)
      api.tag(img.id, repo, tag)
    return img

  def push(self, registry: str=None):
    docker_cli = docker.from_env()
    repo = '%s/%s'%(registry, self.repo) if registry else self.repo
    docker_cli.images.push(repo, self.tag)
  
  def push_aliases(self, registry: str=None):
    if len(self.aliases) == 0:
      return 
    docker_cli = docker.from_env()
    for a in self.aliases:
      repo, tag = a.split(':')
      if registry:
        repo = '%s/%s'%(registry, repo)
      docker_cli.images.push(repo, tag)
  
  def prune(self, registry: str=None):
    docker_cli = docker.from_env()
    docker_cli.images.remove('%s/%s'%(registry, str(self)) if registry else str(self))

  def __str__(self) -> str:
    return Image.ID(self.repo, self.tag)

  def __eq__(self, i) -> bool:
    return isinstance(i, Image) and self.repo == i.repo and self.tag == i.tag 

  def __hash__(self) -> int:
    return hash((self.repo, self.tag))

  
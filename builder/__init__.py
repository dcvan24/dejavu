import os
import queue
import docker
import logging
import requests
import tempfile
import multiprocessing as mp

from typing import Iterable, Dict, List, Tuple

import util
import builder.builder_pb2 as pb2

from base import Image, Layer


class Builder:

  def __init__(self, registry: str, scaling_factor: int, build_dir: str):
    self.__registry = registry
    self.__scaling_factor = scaling_factor
    self.__build_dir = tempfile.mkdtemp(dir=build_dir)

  @property
  def registry(self) -> str:
    return self.__registry

  def build(self, bs: pb2.ImageBuildSet) -> int:
    try:
      new_images, existed = self._filter_existing_images(bs.images)
      layers = self._build_layers(self._get_unique_layers(new_images))
      self._build_images(new_images, existed, layers)
    finally:
      self._clean_up()
    return int(sum(l.size for l in self._get_unique_layers(bs.images)))

  def _filter_existing_images(self, images: Iterable[pb2.Image]) -> List[pb2.Image]:
    man_url_template = 'http://%s/v2/%s/manifests/%s'
    filtered, existed = {}, {}
    for i in images:
      aliases = ['%s:%s'%(i.repo, i.tag)] + list(i.aliases)
      for a in aliases:
        repo, tag = a.split(':')
        r = requests.head(man_url_template%(self.registry, repo, tag))
        if r.ok:
          existed[(i.repo, i.tag)] = i
        else:
          filtered[(i.repo, i.tag)] = i
    logging.info('There are %d/%d new images'%(len(filtered), len(images)))
    return list(filtered.values()), list(existed.values())
  
  def _get_unique_layers(self, images: Iterable[pb2.Image]) -> List[pb2.Layer]:
    layers = {}
    for i in images:
      for l in i.layers:
        layers[l.digest] = l
    return list(layers.values())

  def _build_layers(self, layers: Iterable[pb2.Layer]) -> Dict[str, Layer]:
    layers = {l.digest: Layer(l.digest, l.size) for l in layers}
    n_parallel = int(mp.cpu_count() * self.__scaling_factor)
    sema = mp.Semaphore(n_parallel) 
    build_dir = self.__build_dir
    
    def _build(l):
      with sema:
        l.build(build_dir)

    total_size = int(sum(l.size for l in layers.values()))
    logging.info('Building %d layers in %s, total size: %s'%(len(layers), build_dir, util.size(total_size)))

    wait_q = list(layers.values())
    while len(wait_q) > 0:
      n_procs = min(1000, len(wait_q))
      procs = [mp.Process(target=_build, args=(l, )) for l in wait_q[:n_procs]]
      try:
        for p in procs:
          p.start()
        for p in procs:
          p.join()
      finally:
        for p in procs:
          if p.is_alive(): 
            p.terminate()
      wait_q = wait_q[n_procs:]
    return layers

  def _build_images(self, images: Iterable[pb2.Image], existed: Iterable[pb2.Image], layers: Dict[str, Layer],) -> List[Image]:
    to_build, refs, exist = {}, {}, set()
    for i in existed:
      img = Image(i.repo, i.tag)
      aliases = [str(img)] + list(i.aliases)
      for a in aliases:
        refs[a] = img
        exist.add(a)
    for i in images:
      ls = [layers[l.digest] for l in i.layers if l.digest in layers]
      img = Image(i.repo, i.tag, aliases=i.aliases, layers=ls)
      img_id = str(img)
      to_build[img_id] = img
      aliases = [img_id] + list(i.aliases)
      for a in aliases:
        refs[a] = img
    for i in images:
      if i.parent:
        to_build[Image.ID(i.repo, i.tag)].parent = refs.get(i.parent, Image(*i.parent.split(':')))
    # elect a major image to build and tag other aliases
    elected = set()
    for i in dict(to_build).values():
      elected.add(str(i))
      for a in i.aliases:
        if a not in elected:
          to_build.pop(a, None)

    def _build(idx, total, image):
      with sema:
        logging.info('[%d/%d] Building image %s ...'%(idx, total, image))
        image.build(self.__build_dir, self.registry)
        logging.info('[%d/%d] Pushing image %s to %s ...'%(idx, total, image, self.registry))
        image.push(self.registry)
        logging.info('[%d/%d] Deleting image %s ...'%(idx, total, image))
        image.prune(self.registry)
        if len(image.aliases) > 0:
          logging.info('[%d/%d] Pushing %d aliases of %s to %s ...'%(idx, total, len(image.aliases), image, self.registry))
          image.push_aliases(self.registry)
    
    logging.info('Building a total of %d images'%len(to_build))

    built = set()
    ready = [i for i in to_build.values() if not i.parent or str(i.parent) in built or str(i.parent) in exist]
    while ready:
      procs = [mp.Process(target=_build, args=(len(built) + idx + 1, len(to_build), i, )) for idx, i in enumerate(ready)]
      sema = mp.Semaphore(min(int(mp.cpu_count() * self.__scaling_factor), len(ready)))
      logging.info('Building %d images'%len(procs))
      try:
        for p in procs:
          p.start()
        for p in procs:
          p.join()
      finally:
        for p in procs:
          if p.is_alive():
            p.terminate()
      for i in ready:
        built.add(str(i))
        del to_build[str(i)]
      ready = [i for i in to_build.values() if not i.parent or str(i.parent) in built or str(i.parent) in exist]
    logging.info('Built %d images'%len(built))
    return list(to_build.values())
  
  def _clean_up(self):
    cli = docker.from_env()
    cli.images.prune({'dangling': False})
    os.system('rm -rf %s'%self.__build_dir)
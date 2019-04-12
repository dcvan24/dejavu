import queue
import shutil
import logging
import tempfile
import multiprocessing as mp

from typing import Iterable, Dict, List

import builder.builder_pb2 as pb2

from base import Image, Layer
from util import size

PARALLEL_SCALER = 2

class Builder:

  def __init__(self, registry: str, build_dir: str='/tmp'):
    self.__registry = registry
    self.__build_dir = tempfile.mkdtemp(dir=build_dir)

  @property
  def registry(self) -> str:
    return self.__registry

  def build(self, bs: pb2.ImageBuildSet) -> List[Image]:
    try:
      images = {Image.ID(i.repo, i.tag): i for i in bs.images}.values()
      layers = {l.digest: l for i in images for l in i.layers}.values()
      layers = self._build_layers(layers)
      images = self._build_images(bs.images, layers)
    finally:
      self._clean_up()
    return images

  def _build_layers(self, layers: Iterable[pb2.Layer]) -> Dict[str, Layer]:
    layers = {l.digest: Layer(l.digest, l.size) for l in layers}
    sema, ex_q = mp.Semaphore(mp.cpu_count() * PARALLEL_SCALER), queue.Queue()
    build_dir = self.__build_dir
    
    def _build(l):
      try:
        with sema:
          l.build(build_dir)
      except Exception as e:
        logging.exception('error building layer %s'%l.digest)
        ex_q.put_nowait(e)

    total_size = size(sum(l.size for l in layers.values()))
    logging.debug('Building %d layers in %s, total size: %s'%(len(layers), build_dir, total_size))
    procs = [mp.Process(target=_build, args=(l, )) for l in layers.values()]
    try:
      for p in procs:
        p.start()
      for p in procs:
        p.join()
    finally:
      for p in procs:
        if p.is_alive(): 
          p.terminate()
    if not ex_q.empty():
      raise ex_q.get_nowait()
    return layers

  def _build_images(self, images: Iterable[pb2.Image], layers: Dict[str, Layer],) -> List[Image]:
    to_build = {}
    for i in images:
      ls = [layers[l.digest] for l in i.layers if l.digest in layers]
      to_build[Image.ID(i.repo, i.tag)] = Image(i.repo, i.tag, layers=ls)
    sema, ex_q = mp.Semaphore(mp.cpu_count() * PARALLEL_SCALER), queue.Queue()

    def _build(i):
      try:
        with sema:
          logging.debug('Building image %s ...'%i)
          i.build(self.__build_dir, self.registry)
          logging.debug('Pushing image %s to %s ...'%(i, self.registry))
          i.push(self.registry)
          logging.debug('Pruning local copy of image %s ...'%i)
          i.prune(self.registry)
      except Exception as e:
        logging.exception('error building image %s'%i)
        ex_q.put_nowait(e)

    logging.debug('Building %d images'%len(images))
    procs = [mp.Process(target=_build, args=(i, )) for i in to_build.values()]
    for p in procs:
      p.start()
    for p in procs:
      p.join()
    if not ex_q.empty():
      for p in procs:
        if p.is_alive():
          p.terminate()
      raise ex_q.get_nowait()
    return list(to_build.values())
        
  
  def _clean_up(self):
    shutil.rmtree(self.__build_dir)
import queue
import docker
import shutil
import logging
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
      images = {Image.ID(i.repo, i.tag): i for i in bs.images}.values()
      layers = {l.digest: l for i in images for l in i.layers}.values()
      layers, total_size = self._build_layers(layers)
      self._build_images(bs.images, layers)
    finally:
      self._clean_up()
    return total_size

  def _build_layers(self, layers: Iterable[pb2.Layer]) -> Tuple[Dict[str, Layer], int]:
    layers = {l.digest: Layer(l.digest, l.size) for l in layers}
    sema = mp.Semaphore(int(mp.cpu_count() * self.__scaling_factor)) 
    build_dir = self.__build_dir
    
    def _build(l):
      with sema:
        l.build(build_dir)

    total_size = int(sum(l.size for l in layers.values()))
    logging.info('Building %d layers in %s, total size: %s'%(len(layers), build_dir, util.size(total_size)))
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
    return layers, total_size

  def _build_images(self, images: Iterable[pb2.Image], layers: Dict[str, Layer],) -> List[Image]:
    to_build = {}
    for i in images:
      ls = [layers[l.digest] for l in i.layers if l.digest in layers]
      to_build[Image.ID(i.repo, i.tag)] = Image(i.repo, i.tag, aliases=i.aliases, layers=ls)
    for i in images:
      if i.parent:
        to_build[Image.ID(i.repo, i.tag)].parent = to_build[i.parent]
    # elect a major image to build and tag other aliases
    elected = set()
    for i in dict(to_build).values():
      elected.add(str(i))
      for a in i.aliases:
        if a not in elected:
          to_build.pop(a, None)

    def _build(image):
      with sema:
        logging.info('Building image %s ...'%image)
        image.build(self.__build_dir, self.registry)
        logging.info('Pushing image %s to %s ...'%(image, self.registry))
        image.push(self.registry)
        if len(image.aliases) > 0:
          logging.info('Pushing %d aliases of %s to %s ...'%(len(image.aliases), image, self.registry))
          image.push_aliases(self.registry)

    built = set()
    ready = [i for i in to_build.values() if not i.parent or str(i.parent) in built]
    while ready:
      procs = [mp.Process(target=_build, args=(i, ))for i in ready]
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
      ready = [i for i in to_build.values() if not i.parent or str(i.parent) in built]
    logging.info('Built %d images'%len(built))
    return list(to_build.values())
  
  def _clean_up(self):
    cli = docker.from_env()
    cli.images.prune({'dangling': False})
    shutil.rmtree(self.__build_dir)
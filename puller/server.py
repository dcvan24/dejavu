import time 
import grpc 
import logging 

from typing import Generator
from concurrent import futures
from google.protobuf.empty_pb2 import Empty

import util
import puller.puller_pb2 as pb2 
import puller.puller_pb2_grpc as puller_grpc 

from puller import Puller


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ImagePullerServicer(puller_grpc.ImagePullerServicer):

  def __init__(self):
    self.__puller = Puller()
    self.__cfg = pb2.Config()
    self.__space_used = 0

  def SetConfig(self, cfg: pb2.Config, context) -> Empty:
    self.__cfg = cfg
    return Empty()

  def Pull(self, pull_gen: Generator[pb2.ImagePull, None, None], context) -> Generator[pb2.ImagePullSummary, None, None]:
    cfg = self.__cfg
    try:
      if cfg.capacity > 0:
        logging.info('Capacity: %s'%util.size(cfg.capacity))
      for p in pull_gen:
        if cfg.capacity > 0 and self.__space_used > cfg.capacity:
          logging.info('Out of space (capacity: %s, used: %s), pruning ...'%(util.size(cfg.capacity), util.size(self.__space_used)))
          self._prune()
        s = self.__puller.pull_image(p)
        if cfg.capacity > 0:
          new_layers = [l for l in s.layers if not l.exists]
          self.__space_used += sum(l.full_size for l in new_layers)
          if cfg.include_compressed:
            self.__space_used += sum(l.compact_size for l in new_layers)
        yield s
    except GeneratorExit:
      self._prune()
    finally:
      self._prune()

  def Prune(self, empty, context) -> Empty:
    self._prune()
    return Empty()

  def _prune(self):
    self.__puller.prune_images()
    self.__space_used = 0


  

def serve():
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
  puller_grpc.add_ImagePullerServicer_to_server(ImagePullerServicer(), server)
  server.add_insecure_port('[::]:50052')
  server.start()
  try:
    while True:
      time.sleep(24 * 60 * 60)
  except:
    server.stop(0)
  

if __name__ == "__main__":
    serve()
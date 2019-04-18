import os 
import sys

module_dir = '/'.join(os.path.abspath(os.path.dirname(__file__)).split('/')[:-1])
sys.path.append(module_dir)

import time 
import grpc 
import shutil
import logging 
import argparse

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

  def __init__(self, args: argparse.Namespace):
    self.__puller = Puller()
    self.__args = args
    self.__cfg = pb2.Config()
    self.__init_size = 0

  def SetConfig(self, cfg: pb2.Config, context) -> Empty:
    self.__cfg = cfg
    self.__puller.start_dockerd(cfg, self.__args.dockerd_path)
    self.__init_size = util.get_dir_size(self.__args.docker_home)
    return Empty()

  def WarmUp(self, load: pb2.WarmUpLoad, context) -> Generator[pb2.PullerStatus, None, None]:
    cfg, args = self.__cfg, self.__args
    for p in load.pulls:
      self.__puller.warm_up(p)
      space_used = util.get_dir_size(args.docker_home) - self.__init_size
      logging.info('Space: %s/%s'%(util.size(space_used), util.size(cfg.capacity)))
      yield pb2.PullerStatus(capacity=cfg.capacity, level=space_used)

  def Pull(self, pull_gen: Generator[pb2.ImagePull, None, None], context) -> Generator[pb2.ImagePullSummary, None, None]:
    cfg, args = self.__cfg, self.__args
    try:
      for p in pull_gen:
        s = self.__puller.pull_image(p)
        space_used = util.get_dir_size(args.docker_home) - self.__init_size
        logging.info('Space: %s/%s'%(util.size(space_used), util.size(cfg.capacity)))
        s.puller_status.capacity, s.puller_status.level = cfg.capacity, space_used
        yield s
    finally:
      self.__puller.prune_images()
      self._clean_up_docker_images()

  def Prune(self, empty, context) -> Empty:
    self.__puller.prune_images()
    return Empty()

  def _clean_up_docker_images(self):
    args = self.__args
    image_dir = '%s/image/%s'%(args.docker_home, args.graphdriver)
    shutil.rmtree(image_dir)
    layer_dir = '%s/%s'%(args.docker_home, args.graphdriver)
    for d in os.listdir(layer_dir):
      shutil.rmtree('%s/%s'%(layer_dir, d))


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description='Docker image puller GRPC service')
  parser.add_argument('-p', '--port', type=int, default=55001, dest='port', 
                      help='Listening port') 
  parser.add_argument('-d', '--dockerd-path', type=str, default='/usr/bin/dockerd', dest='dockerd_path', 
                      help='Dockerd path')
  parser.add_argument('--docker-home', type=str, default='/var/lib/docker', dest='docker_home', 
                      help='Docker home directory')
  parser.add_argument('--graphdriver', type=str, default='overlay2', dest='graphdriver', 
                      help='Docker graph driver')
  return parser.parse_args()


def serve(args: argparse.Namespace):
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
  puller_grpc.add_ImagePullerServicer_to_server(ImagePullerServicer(args), server)
  server.add_insecure_port('[::]:%d'%args.port)
  server.start()
  logging.info('Image puller service is listening at %d ...'%args.port)
  try:
    while True:
      time.sleep(24 * 60 * 60)
  except:
    server.stop(0)
  

if __name__ == "__main__":
  serve(parse_args())
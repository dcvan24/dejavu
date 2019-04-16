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

  def SetConfig(self, cfg: pb2.Config, context) -> Empty:
    self.__cfg = cfg
    self.__puller.start_dockerd(cfg, self.__args.dockerd_path)
    return Empty()

  def Pull(self, pull_gen: Generator[pb2.ImagePull, None, None], context) -> Generator[pb2.ImagePullSummary, None, None]:
    cfg, args = self.__cfg, self.__args
    try:
      if cfg.capacity > 0:
        logging.info('Capacity: %s'%util.size(cfg.capacity))
      init_size = util.get_dir_size(os.path.join(args.docker_home, args.graphdriver))
      for p in pull_gen:
        space_used = util.get_dir_size(os.path.join(args.docker_home, args.graphdriver)) - init_size
        logging.info('Space: %s/%s'%(util.size(space_used), util.size(cfg.capacity)))
        yield self.__puller.pull_image(p)
    finally:
      self._clean_up_docker_images()
      self._prune()

  def Prune(self, empty, context) -> Empty:
    self._prune()
    return Empty()

  def _prune(self):
    self.__puller.prune_images()
    self.__space_used = 0

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
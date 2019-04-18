import os 
import sys

module_dir = '/'.join(os.path.abspath(os.path.dirname(__file__)).split('/')[:-1])
sys.path.append(module_dir)

import time
import grpc
import logging
import argparse

from concurrent import futures
from google.protobuf import empty_pb2

import builder.builder_pb2 as pb2
import builder.builder_pb2_grpc as builder_grpc

from builder import Builder
from builder.registry import Registry

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ImageBuilderServicer(builder_grpc.ImageBuilderServicer):

  def __init__(self, registry: Registry, args: argparse.Namespace):
    self.__registry = registry
    self.__args = args

  def Build(self, bs: pb2.ImageBuildSet, context) -> pb2.ImageBuildSummary:
    args = self.__args
    builder = Builder(str(self.__registry), args.scaling_factor, args.build_dir)
    total_size = builder.build(bs)
    return pb2.ImageBuildSummary(total_size=total_size)

  def Purge(self, empty: empty_pb2.Empty, context) -> empty_pb2.Empty:
    self.__registry.purge()
    return empty


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description='Docker image builder GRPC service')
  parser.add_argument('--host', type=str, required=True, dest='host', 
                      help='Binding hostname/IP address')
  parser.add_argument('--port', type=int, default=55000, dest='port', 
                      help='Listening port')
  parser.add_argument('--build-dir', type=str, default='/tmp', dest='build_dir', 
                      help='Build directory')
  parser.add_argument('--scaling-factor', type=float, default=2., dest='scaling_factor', 
                      help='Scaling factor of parallel build')
  parser.add_argument('--registry-dir', type=str, required=True, dest='reg_dir', 
                      help='Docker registry data directory')
  parser.add_argument('--registry-port', type=int, default=5000, dest='reg_port', 
                      help='Docker registry listening port')
  parser.add_argument('--registry-container', type=str, default='registry', dest='reg_contr_id', 
                      help='Docker registry container ID')
  return parser.parse_args()
  

def serve(args: argparse.Namespace):
  registry = Registry(args.host, args.reg_port, args.reg_dir, args.reg_contr_id)
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
  builder_grpc.add_ImageBuilderServicer_to_server(
    ImageBuilderServicer(registry, args), server)
  server.add_insecure_port('[::]:%d'%args.port)
  server.start()
  logging.info('Image builder service is listening at %d ...'%args.port)
  try:
    while True:
      time.sleep(24 * 60 * 60)
  except:
    server.stop(0)

if __name__ == "__main__":
  serve(parse_args())
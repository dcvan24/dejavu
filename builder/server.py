import time
import grpc
import logging

from concurrent import futures
from google.protobuf import empty_pb2

import builder.builder_pb2 as pb2
import builder.builder_pb2_grpc as builder_grpc

from builder import Builder
from builder.registry import Registry

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class ImageBuilderServicer(builder_grpc.ImageBuilderServicer):

  def __init__(self, registry: Registry):
    self.__registry = registry

  def Build(self, bs: pb2.ImageBuildSet, context) -> pb2.BuilderResponse:
    try:
      builder = Builder(str(self.__registry))
      builder.build(bs)
      status, msg = 200, 'Built images successfully'
    except Exception as e:
      logging.exception('Error')
      status, msg = 500, str(e)
    return pb2.BuilderResponse(code=status, message=msg)

  def Purge(self, empty: empty_pb2.Empty, context) -> pb2.BuilderResponse:
    try:
      self.__registry.purge()
      status, msg = 200, 'Registry has been purged successfully'
    except Exception as e:
      status, msg = 500, str(e)
    return pb2.BuilderResponse(code=status, message=msg)

def serve():
  registry = Registry('localhost', 5000)
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
  builder_grpc.add_ImageBuilderServicer_to_server(ImageBuilderServicer(registry), server)
  server.add_insecure_port('[::]:50051')
  server.start()
  try:
    while True:
      time.sleep(24 * 60 * 60)
  except:
    server.stop(0)


if __name__ == "__main__":
  serve()    
    

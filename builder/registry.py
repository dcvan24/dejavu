import os 
import docker
import shutil
import logging 


class Registry:

  def __init__(self, addr: str,  port: int = 5000, 
               base_dir: str = '%s/registry'%os.path.expanduser('~'), 
               container_id: str = 'registry'):
    self.__addr = addr 
    self.__port = port
    self.__base_dir = base_dir 
    self.__contr_id = container_id

  @property
  def address(self) -> str:
    return self.__addr

  @property
  def port(self) -> int:
    return self.__port

  def purge(self):
    base_dir, contr_id = self.__base_dir, self.__contr_id
    cli = docker.from_env()
    if not os.path.exists(base_dir):
      return 
    try:
      logging.debug('Removing registry data directory [%s] ...'%base_dir)
      for d in os.listdir(base_dir):
        shutil.rmtree('%s/%s'%(base_dir, d))
      logging.debug('Restarting registry container [%s] ...'%contr_id)
      c = cli.containers.get(contr_id)
      c.restart
    except docker.errors.NotFound:
      logging.warn('The registry [%s] is not running'%contr_id)

  def __str__(self):
    return '%s:%d'%(self.address, self.port)

  
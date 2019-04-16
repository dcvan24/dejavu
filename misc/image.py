import os
import sys 

proj_path = '/'.join(os.path.abspath(os.path.dirname(__file__)).split('/')[:-1])
sys.path += proj_path,

import json 
import numpy as np

from collections import defaultdict

import util
import builder.builder_pb2 as pb2

from base import Image


DATA_CENTER = 'syd01'
REGISTRY = 'localhost:5000'

MIN_THROUGHPUT = 100 # bytes/second 
MIN_DIFF = 100


def parse_images(data_center, prefix='../data/clean_data', min_throughput=100, min_diff=100):
  images = {}
  data_dir = '%s/%s'%(prefix, data_center)
  for c in os.listdir(data_dir):
    with open('%s/%s'%(data_dir, c)) as f:
      cur_pulls = {}
      for i, e in enumerate(json.load(f)):
        repo, etype, tag = util.parse_uri(e['uri'])
        if repo is None:
          continue
        if etype == 'manifests':
          img = Image(repo, tag)  
          img = images.setdefault(str(img), img)
          cur_pulls[repo] = img
        else:
          img = cur_pulls.get(repo)
          if img is None:
            continue
          dgst = tag
          img.add_layer(dgst, e['size'])
  return {img_id: img for img_id, img in images.items() if len(img.layers) > 0}


def load_images(data_center, prefix='../data/images'):
  data_dir = '%s/%s'%(prefix, data_center)
  with open('%s/layers.json'%data_dir) as f:
    layers = {l['digest']: l for l in json.load(f)}
  with open('%s/images.json'%data_dir) as f:
    images = {}
    for i in json.load(f):
      img = pb2.Image(repo=i['repo'], tag=i['tag'], 
                      parent=i['parent'], aliases=i['aliases'],
                      layers=[pb2.Layer(digest=dgst, size=layers[dgst]['size']) 
                              for dgst in i['layers']])
      images[Image.ID(img.repo, img.tag)] = img
  return images


def save_images(images, data_center, dest='../data/images'):
  print('Saving images ...')
  data_dir = '%s/%s'%(dest, data_center)
  os.makedirs(data_dir, exist_ok=True)
  images = list(images.values())
  for i in images:
    i.squash_layers()
  layers = set(l for i in images for l in i.layers)
  with open('%s/images.json'%data_dir, 'w') as f:
    json.dump([i.to_json() for i in images], f, indent=2)
  with open('%s/layers.json'%data_dir, 'w') as f:
    json.dump([l.to_json() for l in layers], f, indent=2)


def resolve_image_dependencies(images):
  layer_map = defaultdict(list)
  for img in images.values():
    for l in img.layers:
      layer_map[l.digest] += img, 
  dep_count, alias_count = 0, 0
  for img in images.values():
    for l in img.layers:
      for p in layer_map[l.digest]:
        if p == img:
          continue
        if img.is_child(p):
          print('%s -> %s, parent: %d, child: %d'%(p, img, len(p.layers), len(img.layers)))
          img.parent = p
          dep_count += 1
        elif img.has_alias(p):
          print('%s == %s, # of layers: %d'%(p, img, len(p.layers)))
          img.add_alias(p)
          alias_count += 1
  print('Find %d dependencies among %d images'%(dep_count, len(images)))
  print('Find %d aliases'%(alias_count/2))
  return images

if __name__ == '__main__':
  images = parse_images(DATA_CENTER)
  resolve_image_dependencies(images)
  for i in images.values():
    i.squash_layers()
  save_images(images, DATA_CENTER)
  total_size = sum(l.size for i in images.values() for l in i.layers)
  print('Total size: %s'%util.size(total_size))
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: builder.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='builder.proto',
  package='dejavu.builder',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\rbuilder.proto\x12\x0e\x64\x65javu.builder\x1a\x1bgoogle/protobuf/empty.proto\"I\n\x05Image\x12\x0c\n\x04repo\x18\x01 \x01(\t\x12\x0b\n\x03tag\x18\x02 \x01(\t\x12%\n\x06layers\x18\x03 \x03(\x0b\x32\x15.dejavu.builder.Layer\"%\n\x05Layer\x12\x0e\n\x06\x64igest\x18\x01 \x01(\t\x12\x0c\n\x04size\x18\x02 \x01(\x04\"6\n\rImageBuildSet\x12%\n\x06images\x18\x01 \x03(\x0b\x32\x15.dejavu.builder.Image\"0\n\x0f\x42uilderResponse\x12\x0c\n\x04\x63ode\x18\x01 \x01(\r\x12\x0f\n\x07message\x18\x02 \x01(\t2\x9d\x01\n\x0cImageBuilder\x12I\n\x05\x42uild\x12\x1d.dejavu.builder.ImageBuildSet\x1a\x1f.dejavu.builder.BuilderResponse\"\x00\x12\x42\n\x05Purge\x12\x16.google.protobuf.Empty\x1a\x1f.dejavu.builder.BuilderResponse\"\x00\x62\x06proto3')
  ,
  dependencies=[google_dot_protobuf_dot_empty__pb2.DESCRIPTOR,])




_IMAGE = _descriptor.Descriptor(
  name='Image',
  full_name='dejavu.builder.Image',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='repo', full_name='dejavu.builder.Image.repo', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='tag', full_name='dejavu.builder.Image.tag', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='layers', full_name='dejavu.builder.Image.layers', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=62,
  serialized_end=135,
)


_LAYER = _descriptor.Descriptor(
  name='Layer',
  full_name='dejavu.builder.Layer',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='digest', full_name='dejavu.builder.Layer.digest', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='size', full_name='dejavu.builder.Layer.size', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=137,
  serialized_end=174,
)


_IMAGEBUILDSET = _descriptor.Descriptor(
  name='ImageBuildSet',
  full_name='dejavu.builder.ImageBuildSet',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='images', full_name='dejavu.builder.ImageBuildSet.images', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=176,
  serialized_end=230,
)


_BUILDERRESPONSE = _descriptor.Descriptor(
  name='BuilderResponse',
  full_name='dejavu.builder.BuilderResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='code', full_name='dejavu.builder.BuilderResponse.code', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='message', full_name='dejavu.builder.BuilderResponse.message', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=232,
  serialized_end=280,
)

_IMAGE.fields_by_name['layers'].message_type = _LAYER
_IMAGEBUILDSET.fields_by_name['images'].message_type = _IMAGE
DESCRIPTOR.message_types_by_name['Image'] = _IMAGE
DESCRIPTOR.message_types_by_name['Layer'] = _LAYER
DESCRIPTOR.message_types_by_name['ImageBuildSet'] = _IMAGEBUILDSET
DESCRIPTOR.message_types_by_name['BuilderResponse'] = _BUILDERRESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Image = _reflection.GeneratedProtocolMessageType('Image', (_message.Message,), dict(
  DESCRIPTOR = _IMAGE,
  __module__ = 'builder_pb2'
  # @@protoc_insertion_point(class_scope:dejavu.builder.Image)
  ))
_sym_db.RegisterMessage(Image)

Layer = _reflection.GeneratedProtocolMessageType('Layer', (_message.Message,), dict(
  DESCRIPTOR = _LAYER,
  __module__ = 'builder_pb2'
  # @@protoc_insertion_point(class_scope:dejavu.builder.Layer)
  ))
_sym_db.RegisterMessage(Layer)

ImageBuildSet = _reflection.GeneratedProtocolMessageType('ImageBuildSet', (_message.Message,), dict(
  DESCRIPTOR = _IMAGEBUILDSET,
  __module__ = 'builder_pb2'
  # @@protoc_insertion_point(class_scope:dejavu.builder.ImageBuildSet)
  ))
_sym_db.RegisterMessage(ImageBuildSet)

BuilderResponse = _reflection.GeneratedProtocolMessageType('BuilderResponse', (_message.Message,), dict(
  DESCRIPTOR = _BUILDERRESPONSE,
  __module__ = 'builder_pb2'
  # @@protoc_insertion_point(class_scope:dejavu.builder.BuilderResponse)
  ))
_sym_db.RegisterMessage(BuilderResponse)



_IMAGEBUILDER = _descriptor.ServiceDescriptor(
  name='ImageBuilder',
  full_name='dejavu.builder.ImageBuilder',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=283,
  serialized_end=440,
  methods=[
  _descriptor.MethodDescriptor(
    name='Build',
    full_name='dejavu.builder.ImageBuilder.Build',
    index=0,
    containing_service=None,
    input_type=_IMAGEBUILDSET,
    output_type=_BUILDERRESPONSE,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='Purge',
    full_name='dejavu.builder.ImageBuilder.Purge',
    index=1,
    containing_service=None,
    input_type=google_dot_protobuf_dot_empty__pb2._EMPTY,
    output_type=_BUILDERRESPONSE,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_IMAGEBUILDER)

DESCRIPTOR.services_by_name['ImageBuilder'] = _IMAGEBUILDER

# @@protoc_insertion_point(module_scope)
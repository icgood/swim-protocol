"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.internal.enum_type_wrapper
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

global___SwimStatus = SwimStatus
class _SwimStatus(google.protobuf.internal.enum_type_wrapper._EnumTypeWrapper[SwimStatus.V], builtins.type):
    DESCRIPTOR: google.protobuf.descriptor.EnumDescriptor = ...
    OFFLINE = SwimStatus.V(0)
    ONLINE = SwimStatus.V(1)
    SUSPECT = SwimStatus.V(2)
class SwimStatus(metaclass=_SwimStatus):
    V = typing.NewType('V', builtins.int)
OFFLINE = SwimStatus.V(0)
ONLINE = SwimStatus.V(1)
SUSPECT = SwimStatus.V(2)

class SwimPing(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...

    def __init__(self,
        ) -> None: ...
global___SwimPing = SwimPing

class SwimPingReq(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    TARGET_FIELD_NUMBER: builtins.int
    target: typing.Text = ...

    def __init__(self,
        *,
        target : typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"target",b"target"]) -> None: ...
global___SwimPingReq = SwimPingReq

class SwimAck(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    ONLINE_FIELD_NUMBER: builtins.int
    online: builtins.bool = ...

    def __init__(self,
        *,
        online : builtins.bool = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"online",b"online"]) -> None: ...
global___SwimAck = SwimAck

class SwimUpdate(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    class MetadataEntry(google.protobuf.message.Message):
        DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
        KEY_FIELD_NUMBER: builtins.int
        VALUE_FIELD_NUMBER: builtins.int
        key: typing.Text = ...
        value: typing.Text = ...

        def __init__(self,
            *,
            key : typing.Text = ...,
            value : typing.Text = ...,
            ) -> None: ...
        def ClearField(self, field_name: typing_extensions.Literal[u"key",b"key",u"value",b"value"]) -> None: ...

    ADDRESS_FIELD_NUMBER: builtins.int
    CLOCK_FIELD_NUMBER: builtins.int
    STATUS_FIELD_NUMBER: builtins.int
    METADATA_FIELD_NUMBER: builtins.int
    address: typing.Text = ...
    clock: builtins.int = ...
    status: global___SwimStatus.V = ...

    @property
    def metadata(self) -> google.protobuf.internal.containers.ScalarMap[typing.Text, typing.Text]: ...

    def __init__(self,
        *,
        address : typing.Text = ...,
        clock : builtins.int = ...,
        status : global___SwimStatus.V = ...,
        metadata : typing.Optional[typing.Mapping[typing.Text, typing.Text]] = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"address",b"address",u"clock",b"clock",u"metadata",b"metadata",u"status",b"status"]) -> None: ...
global___SwimUpdate = SwimUpdate

class SwimGossip(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    SOURCE_FIELD_NUMBER: builtins.int
    UPDATES_FIELD_NUMBER: builtins.int
    source: typing.Text = ...

    @property
    def updates(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___SwimUpdate]: ...

    def __init__(self,
        *,
        source : typing.Text = ...,
        updates : typing.Optional[typing.Iterable[global___SwimUpdate]] = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal[u"source",b"source",u"updates",b"updates"]) -> None: ...
global___SwimGossip = SwimGossip
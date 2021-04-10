# Generated by the Protocol Buffers compiler. DO NOT EDIT!
# source: swimprotocol/grpc/swimprotocol.proto
# plugin: grpclib.plugin.main
import abc
import typing

import grpclib.const
import grpclib.client
if typing.TYPE_CHECKING:
    import grpclib.server

import swimprotocol.grpc.swimprotocol_pb2


class SwimProtocolBase(abc.ABC):

    @abc.abstractmethod
    async def PingCommand(self, stream: 'grpclib.server.Stream[swimprotocol.grpc.swimprotocol_pb2.Ping, swimprotocol.grpc.swimprotocol_pb2.Ack]') -> None:
        pass

    @abc.abstractmethod
    async def PingReqCommand(self, stream: 'grpclib.server.Stream[swimprotocol.grpc.swimprotocol_pb2.PingReq, swimprotocol.grpc.swimprotocol_pb2.Ack]') -> None:
        pass

    @abc.abstractmethod
    async def SyncCommand(self, stream: 'grpclib.server.Stream[swimprotocol.grpc.swimprotocol_pb2.Gossip, swimprotocol.grpc.swimprotocol_pb2.Gossip]') -> None:
        pass

    def __mapping__(self) -> typing.Dict[str, grpclib.const.Handler]:
        return {
            '/swimprotocol.grpc.SwimProtocol/PingCommand': grpclib.const.Handler(
                self.PingCommand,
                grpclib.const.Cardinality.UNARY_UNARY,
                swimprotocol.grpc.swimprotocol_pb2.Ping,
                swimprotocol.grpc.swimprotocol_pb2.Ack,
            ),
            '/swimprotocol.grpc.SwimProtocol/PingReqCommand': grpclib.const.Handler(
                self.PingReqCommand,
                grpclib.const.Cardinality.UNARY_UNARY,
                swimprotocol.grpc.swimprotocol_pb2.PingReq,
                swimprotocol.grpc.swimprotocol_pb2.Ack,
            ),
            '/swimprotocol.grpc.SwimProtocol/SyncCommand': grpclib.const.Handler(
                self.SyncCommand,
                grpclib.const.Cardinality.UNARY_UNARY,
                swimprotocol.grpc.swimprotocol_pb2.Gossip,
                swimprotocol.grpc.swimprotocol_pb2.Gossip,
            ),
        }


class SwimProtocolStub:

    def __init__(self, channel: grpclib.client.Channel) -> None:
        self.PingCommand = grpclib.client.UnaryUnaryMethod(
            channel,
            '/swimprotocol.grpc.SwimProtocol/PingCommand',
            swimprotocol.grpc.swimprotocol_pb2.Ping,
            swimprotocol.grpc.swimprotocol_pb2.Ack,
        )
        self.PingReqCommand = grpclib.client.UnaryUnaryMethod(
            channel,
            '/swimprotocol.grpc.SwimProtocol/PingReqCommand',
            swimprotocol.grpc.swimprotocol_pb2.PingReq,
            swimprotocol.grpc.swimprotocol_pb2.Ack,
        )
        self.SyncCommand = grpclib.client.UnaryUnaryMethod(
            channel,
            '/swimprotocol.grpc.SwimProtocol/SyncCommand',
            swimprotocol.grpc.swimprotocol_pb2.Gossip,
            swimprotocol.grpc.swimprotocol_pb2.Gossip,
        )

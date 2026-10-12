import time

from ..idl.unitree_api.msg.dds_ import Request_ as Request
from ..idl.unitree_api.msg.dds_ import RequestHeader_ as RequestHeader
from ..idl.unitree_api.msg.dds_ import RequestLease_ as RequestLease
from ..idl.unitree_api.msg.dds_ import RequestIdentity_ as RequestIdentity
from ..idl.unitree_api.msg.dds_ import RequestPolicy_ as RequestPolicy

from ..utils.future import FutureResult

from .client_stub import ClientStub
from .internal import *


"""
" class ClientBase
"""
class ClientBase:
    """RPC 客户端基类，负责封装请求、发送数据、等待响应和处理通信错误。"""

    def __init__(self, serviceName: str):
        """创建指定服务的通信代理并初始化发送、接收通道。

        serviceName 为机器人服务名称；默认通信超时时间为 1 秒。
        """
        self.__timeout = 1.0
        self.__stub = ClientStub(serviceName)
        self.__stub.Init()

    def SetTimeout(self, timeout: float):
        """设置通信超时时间，单位为秒。

        发送阶段和等待响应阶段分别使用该值，不是整个调用的总时限。
        此方法只保存设置，不会等待，也不控制机器人动作的持续时间。
        """
        self.__timeout = timeout

    def _CallBase(self, apiId: int, parameter: str, proirity: int = 0, leaseId: int = 0):
        """发送字符串参数请求，等待响应并返回字符串数据。

        参数：
            apiId: 要调用的接口编号。
            parameter: 请求参数字符串，通常由上层序列化为 JSON。
            proirity: 请求优先级（参数名沿用现有拼写）。
            leaseId: 请求携带的租约 ID。
        返回：
            (服务端状态码, response.data)；通信失败时返回 (错误码, None)。
        """
        # print("[CallBase] call apiId:", apiId, ", proirity:", proirity, ", leaseId:", leaseId)
        # noReply=False 表示需要回复；第三个字段为空，表示不携带二进制数据。
        header = self.__SetHeader(apiId, leaseId, proirity, False)
        request = Request(header, parameter, [])

        # 发送请求，取得用于接收这次响应的 Future。
        future = self.__stub.SendRequest(request, self.__timeout)
        if future is None:
            return RPC_ERR_CLIENT_SEND, None

        # 等待响应到达；发送阶段和此处的等待分别使用超时设置。
        result = future.GetResult(self.__timeout)

        if result.code != FutureResult.FUTURE_SUCC:
            # 超时或等待失败后，清理该请求的等待记录并转换为 RPC 错误码。
            self.__stub.RemoveFuture(request.header.identity.id)
            code = RPC_ERR_CLIENT_API_TIMEOUT if result.code == FutureResult.FUTUTE_ERR_TIMEOUT else RPC_ERR_UNKNOWN
            return code, None

        response = result.value

        # 确认响应的接口编号与本次调用一致。
        if response.header.identity.api_id != apiId:
            return RPC_ERR_CLIENT_API_NOT_MATCH, None
        else:
            return response.header.status.code, response.data

    def _CallNoReplyBase(self, apiId: int, parameter: str, proirity: int, leaseId: int):
        """发送字符串参数请求，不等待服务端回复。

        apiId 为接口编号，parameter 为参数字符串，proirity 为请求优先级，
        leaseId 为租约 ID。返回 0 表示发送成功，失败返回发送错误码；
        发送成功不代表机器人已完成动作。
        """
        header = self.__SetHeader(apiId, leaseId, proirity, True)
        request = Request(header, parameter, [])

        if self.__stub.Send(request, self.__timeout):
            return 0
        else:
            return RPC_ERR_CLIENT_SEND

    def _CallRequestWithParamAndBinBase(self, apiId: int, requestParamter: str,
                                        requestBinary: list, proirity: int = 0,
                                        leaseId: int = 0):
        """同时发送字符串参数和二进制数据，等待响应并返回字符串数据。

        apiId 为接口编号，requestParamter 为参数字符串，requestBinary 为
        二进制数据列表，proirity 为请求优先级，leaseId 为租约 ID。
        返回 (服务端状态码, response.data)；通信失败返回 (错误码, None)。
        """
        header = self.__SetHeader(apiId, leaseId, proirity, False)
        request = Request(header, requestParamter, requestBinary)

        future = self.__stub.SendRequest(request, self.__timeout)
        if future is None:
            return RPC_ERR_CLIENT_SEND, None

        result = future.GetResult(self.__timeout)

        if result.code != FutureResult.FUTURE_SUCC:
            self.__stub.RemoveFuture(request.header.identity.id)
            code = RPC_ERR_CLIENT_API_TIMEOUT if result.code == FutureResult.FUTUTE_ERR_TIMEOUT else RPC_ERR_UNKNOWN
            return code, None

        response = result.value

        if response.header.identity.api_id != apiId:
            return RPC_ERR_CLIENT_API_NOT_MATCH, None
        else:
            return response.header.status.code, response.data

    def _CallRequestWithParamAndBinNoReplyBase(self, apiId: int, requestParamter: str,
                                               requestBinary: list, proirity: int,
                                               leaseId: int):
        """用于同时发送字符串参数和二进制数据，不等待服务端回复。

        apiId 为接口编号，requestParamter 为参数字符串，requestBinary 为
        二进制数据列表，proirity 为请求优先级，leaseId 为租约 ID。
        设计返回值为：发送成功返回 0，发送失败返回发送错误码。
        当前实现引用了未定义的 request_binary，调用时会触发 NameError。
        """
        header = self.__SetHeader(apiId, leaseId, proirity, True)
        request = Request(header, requestParamter, request_binary)

        if self.__stub.Send(request, self.__timeout):
            return 0
        else:
            return RPC_ERR_CLIENT_SEND

    def _CallBinaryBase(self, apiId: int, parameter: list, proirity: int, leaseId: int):
        """发送二进制数据请求，等待响应并返回二进制数据。

        apiId 为接口编号，parameter 为二进制数据列表，proirity 为请求
        优先级，leaseId 为租约 ID；请求中的字符串参数字段为空。
        返回 (服务端状态码, response.binary)；通信失败返回 (错误码, None)。
        """
        header = self.__SetHeader(apiId, leaseId, proirity, False)
        request = Request(header, "", parameter)
        
        future = self.__stub.SendRequest(request, self.__timeout)
        if future is None:
            return RPC_ERR_CLIENT_SEND, None

        result = future.GetResult(self.__timeout)
        if result.code != FutureResult.FUTURE_SUCC:
            self.__stub.RemoveFuture(request.header.identity.id)
            code = RPC_ERR_CLIENT_API_TIMEOUT if result.code == FutureResult.FUTUTE_ERR_TIMEOUT else RPC_ERR_UNKNOWN
            return code, None

        response = result.value

        if response.header.identity.api_id != apiId:
            return RPC_ERR_CLIENT_API_NOT_MATCH, None
        else:
            return response.header.status.code, response.binary

    def _CallBinaryNoReplyBase(self, apiId: int, parameter: list, proirity: int, leaseId: int):
        """发送二进制数据请求，不等待服务端回复。

        apiId 为接口编号，parameter 为二进制数据列表，proirity 为请求
        优先级，leaseId 为租约 ID。返回 0 表示发送成功，失败返回发送错误码；
        返回值不反映服务端是否执行成功。
        """
        header = self.__SetHeader(apiId, leaseId, proirity, True)
        request = Request(header, "", parameter)

        if self.__stub.Send(request, self.__timeout):
            return 0
        else:
            return RPC_ERR_CLIENT_SEND
    
    def __SetHeader(self, apiId: int, leaseId: int, priority: int, noReply: bool):
        """构造并返回请求头，供各类调用方法使用。

        使用单调时钟的纳秒值生成请求 ID，供通信代理关联请求和响应。
        apiId 为接口编号，leaseId 为租约 ID，priority 为请求优先级；
        noReply=True 表示不需要服务端回复，False 表示需要回复。
        """
        identity = RequestIdentity(time.monotonic_ns(), apiId)
        lease = RequestLease(leaseId)
        policy = RequestPolicy(priority, noReply)
        return RequestHeader(identity, lease, policy)

import json

from ...rpc.client import Client
from .motion_switcher_api import *

"""
" class MotionSwitcherClient
"""
class MotionSwitcherClient(Client):
    """运动模式切换服务的 RPC 客户端，用于查询、选择和释放运动模式。

    使用前先初始化 ChannelFactory，再创建客户端、设置超时并调用 Init()。
    各操作返回 (code, result)：code 为 0 表示调用成功，非 0 表示错误。
    具体模式名称及切换行为由机器人端服务决定。
    """

    def __init__(self):
        """创建 motion_switcher 服务客户端，不启用租约机制。"""
        # 父类负责初始化 RPC 通信；False 表示不使用 LeaseClient 管理租约。
        super().__init__(MOTION_SWITCHER_SERVICE_NAME, False)


    def Init(self):
        """设置本地 API 版本并注册接口；本方法不发送模式切换请求。"""
        # 保存本客户端使用的 API 版本，当前常量为 "1.0.0.1"。
        self._SetApiVerson(MOTION_SWITCHER_API_VERSION)

        # 在父类中登记可调用的 API，第二个参数 0 是请求优先级。
        # _Call() 会先检查接口是否已注册，因此调用业务方法前需要 Init()。
        self._RegistApi(MOTION_SWITCHER_API_ID_CHECK_MODE, 0)
        self._RegistApi(MOTION_SWITCHER_API_ID_SELECT_MODE, 0)
        self._RegistApi(MOTION_SWITCHER_API_ID_RELEASE_MODE, 0)
        # 1004、1005 也进行了注册，但本类尚未提供对应的公开调用方法。
        self._RegistApi(MOTION_SWITCHER_API_ID_SET_SILENT, 0)
        self._RegistApi(MOTION_SWITCHER_API_ID_GET_SILENT, 0)

    def CheckMode(self):
        """查询当前运动模式（API 1001）。

        成功返回 (0, JSON 解码后的模式信息)，失败返回 (错误码, None)。
        仓库示例通过结果中的 "name" 判断是否存在活动模式：空字符串表示
        无活动模式。读取结果前应先确认 code == 0。
        若成功响应中的 data 不是有效 JSON，json.loads() 会抛出异常。
        """
        # 查询不需要业务参数，但 RPC 参数字段仍需传入 JSON 字符串 "{}"。
        p = {}
        parameter = json.dumps(p)
        # _Call() 发送请求并等待响应，返回状态码和响应数据字符串。
        code, data = self._Call(MOTION_SWITCHER_API_ID_CHECK_MODE, parameter)
        if code == 0:
            # 将服务端 JSON 字符串转换为 Python 对象，供调用者读取模式信息。
            return code, json.loads(data)
        else:
            return code, None

    def SelectMode(self, nameOrAlias):
        """按名称或别名请求切换运动模式（API 1002）。

        nameOrAlias 为模式名称或别名。仓库示例使用 "ai"，并列出 "normal"、
        "advanced"、"ai-w" 等选项；可用值取决于机器人型号及服务端支持。
        返回 (code, None)，调用者通过 code 判断结果。
        """
        p = {}
        # 服务端约定用 "name" 字段接收模式名称或别名。
        p["name"] = nameOrAlias
        parameter = json.dumps(p)
        code, data = self._Call(MOTION_SWITCHER_API_ID_SELECT_MODE, parameter)

        # 等待 RPC 响应，但不向调用者返回响应正文 data，只保留状态码。
        return code, None

    def ReleaseMode(self):
        """请求释放当前运动模式（API 1003），返回 (code, None)。

        低层控制示例在发送电机指令前调用此方法，释放已有运动模式，避免
        与已有控制器争用。释放后可再次调用 CheckMode() 确认模式状态。
        此方法本身不发送站立、趴下或电机控制指令。
        """
        # 释放当前模式无需指定名称，发送空 JSON 对象即可。
        p = {}
        parameter = json.dumps(p)
        code, data = self._Call(MOTION_SWITCHER_API_ID_RELEASE_MODE, parameter)

        # 与 SelectMode() 一样，保留状态码并忽略响应正文。
        return code, None

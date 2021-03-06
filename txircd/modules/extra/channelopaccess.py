from twisted.plugin import IPlugin
from txircd.module_interface import IMode, IModuleData, Mode, ModuleData
from txircd.utils import ModeType
from zope.interface import implementer
from typing import Callable, List, Optional, Tuple, Union

@implementer(IPlugin, IModuleData, IMode)
class ChannelOpAccess(ModuleData, Mode):
	name = "ChannelOpAccess"
	affectedActions = {
		"checkchannellevel": 10,
		"checkexemptchanops": 10
	}
	
	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("modeactioncheck-channel-W-checkchannellevel", 1, self.checkMode),
		         ("modeactioncheck-channel-W-checkexemptchanops", 1, self.checkMode) ]
	
	def channelModes(self) -> List[Union[Tuple[str, ModeType, Mode], Tuple[str, ModeType, Mode, int, str]]]:
		return [ ("W", ModeType.List, self) ]
	
	def checkMode(self, channel: "IRCChannel", checkType: str, paramChannel: "IRCChannel", user: "IRCUser") -> Union[str, bool, None]:
		if "W" not in channel.modes:
			return None
		for paramData in channel.modes["W"]:
			level, permType = paramData[0].split(":", 1)
			if permType == checkType:
				return paramData[0]
		return None
	
	def checkSet(self, channel: "IRCChannel", param: str) -> Optional[List[str]]:
		checkedParams = []
		for parameter in param.split(","):
			if ":" not in parameter:
				continue
			status, permissionType = parameter.split(":", 1)
			if status not in self.ircd.channelStatuses and status not in ("*", "-"):
				continue
			checkedParams.append(parameter)
		return checkedParams
	
	def apply(self, actionType: str, channel: "IRCChannel", param: str, checkType: str, paramChannel: "IRCChannel", user: "IRCUser") -> Optional[bool]:
		status, permissionType = param.split(":", 1)
		if permissionType != checkType:
			return None
		if status == "*": # Specifying all users
			return True
		if status == "-": # Specifying no users
			return False
		if status not in self.ircd.channelStatuses:
			return False # For security, we'll favor those that were restricting permissions while a certain status was loaded.
		level = self.ircd.channelStatuses[status][1]
		return channel.userRank(user) >= level

chanAccess = ChannelOpAccess()
from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.config import ConfigValidationError
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from txircd.utils import trimStringToByteLength
from zope.interface import implementer
from typing import Any, Callable, Dict, List, Optional, Tuple

@implementer(IPlugin, IModuleData)
class PartCommand(ModuleData):
	name = "PartCommand"
	core = True
	
	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("leavemessage", 101, self.broadcastPart),
		         ("leavemessage", 1, self.sendPartMessage) ]
	
	def userCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("PART", 1, UserPart(self.ircd)) ]
	
	def serverCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("PART", 1, ServerPart(self.ircd)) ]

	def verifyConfig(self, config: Dict[str, Any]) -> None:
		if "part_message_length" in config:
			if not isinstance(config["part_message_length"], int) or config["part_message_length"] < 0:
				raise ConfigValidationError("part_message_length", "invalid number")
			elif config["part_message_length"] > 300:
				config["part_message_length"] = 300
				self.ircd.logConfigValidationWarning("part_message_length", "value is too large", 300)
	
	def broadcastPart(self, sendUserList: List["IRCUser"], channel: "IRCChannel", user: "IRCUser", type: str, typeData: Dict[Any, Any], fromServer: Optional["IRCServer"]) -> None:
		if type != "PART":
			return
		reason = ""
		if "reason" in typeData:
			reason = typeData["reason"]
		self.ircd.broadcastToServers(fromServer, "PART", channel.name, reason, prefix=user.uuid)
	
	def sendPartMessage(self, sendUserList: List["IRCUser"], channel: "IRCChannel", user: "IRCUser", type: str, typeData: Dict[Any, Any], fromServer: Optional["IRCServer"]) -> None:
		if type != "PART":
			return
		msgPrefix = user.hostmask()
		conditionalTags = {}
		self.ircd.runActionStandard("sendingusertags", user, conditionalTags)
		if "reason" in typeData and typeData["reason"]:
			reason = typeData["reason"]
			for destUser in sendUserList:
				if destUser.uuid[:3] == self.ircd.serverID:
					tags = destUser.filterConditionalTags(conditionalTags)
					destUser.sendMessage("PART", reason, to=channel.name, prefix=msgPrefix, tags=tags)
		else:
			for destUser in sendUserList:
				if destUser.uuid[:3] == self.ircd.serverID:
					tags = destUser.filterConditionalTags(conditionalTags)
					destUser.sendMessage("PART", to=channel.name, prefix=msgPrefix, tags=tags)
		del sendUserList[:]

@implementer(ICommand)
class UserPart(Command):
	def __init__(self, ircd):
		self.ircd = ircd
	
	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		if not params or not params[0]:
			user.sendSingleError("PartCmd", irc.ERR_NEEDMOREPARAMS, "PART", "Not enough parameters")
			return None
		if params[0] not in self.ircd.channels:
			user.sendSingleError("PartCmd", irc.ERR_NOSUCHCHANNEL, params[0], "No such channel")
			return None
		channel = self.ircd.channels[params[0]]
		if user not in channel.users:
			user.sendSingleError("PartCmd", irc.ERR_NOTONCHANNEL, params[0], "You're not on that channel")
			return None
		reason = params[1] if len(params) > 1 else ""
		reason = trimStringToByteLength(reason, self.ircd.config.get("part_message_length", 300))
		return {
			"channel": channel,
			"reason": reason
		}
	
	def affectedChannels(self, user: "IRCUser", data: Dict[Any, Any]) -> List["IRCChannel"]:
		return [ data["channel"] ]
	
	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		channel = data["channel"]
		reason = data["reason"]
		user.leaveChannel(channel, "PART", { "reason": reason })
		return True

@implementer(ICommand)
class ServerPart(Command):
	burstQueuePriority = 72
	
	def __init__(self, ircd):
		self.ircd = ircd
	
	def parseParams(self, server: "IRCServer", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		if len(params) != 2 or not params[0]:
			return None
		if prefix not in self.ircd.users:
			if prefix in self.ircd.recentlyQuitUsers:
				return {
					"lostuser": True
				}
			return None
		if params[0] not in self.ircd.channels:
			if params[0] in self.ircd.recentlyDestroyedChannels:
				return {
					"lostchannel": True
				}
			return None
		return {
			"user": self.ircd.users[prefix],
			"channel": self.ircd.channels[params[0]],
			"reason": params[1]
		}
	
	def execute(self, server: "IRCServer", data: Dict[Any, Any]) -> bool:
		if "lostuser" in data or "lostchannel" in data:
			return True
		user = data["user"]
		channel = data["channel"]
		reason = data["reason"]
		user.leaveChannel(channel, "PART", { "reason": reason }, server)
		return True

partCommand = PartCommand()
from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData, ModuleData
from zope.interface import implementer
from typing import Any, Callable, Dict, List, Optional, Tuple

@implementer(IPlugin, IModuleData)
class EchoMessage(ModuleData):
	name = "EchoMessage"
	
	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("commandextra-PRIVMSG", 10, self.returnPrivMsgMessage),
		         ("commandextra-NOTICE", 10, self.returnNoticeMessage),
		         ("capabilitylist", 10, self.addCapability) ]
	
	def load(self) -> None:
		if "unloading-echo-message" in self.ircd.dataCache:
			del self.ircd.dataCache["unloading-echo-message"]
			return
		if "cap-add" in self.ircd.functionCache:
			self.ircd.functionCache["cap-add"]("echo-message")
	
	def unload(self) -> Optional["Deferred"]:
		self.ircd.dataCache["unloading-echo-message"] = True
	
	def fullUnload(self) -> Optional["Deferred"]:
		del self.ircd.dataCache["unloading-echo-message"]
		if "cap-del" in self.ircd.functionCache:
			self.ircd.functionCache["cap-del"]("echo-message")
	
	def addCapability(self, user: "IRCUser", capList: List[str]) -> None:
		capList.append("echo-message")
	
	def returnPrivMsgMessage(self, user: "IRCUser", data: Dict[Any, Any]) -> None:
		self.returnMessage("PRIVMSG", user, data)
	
	def returnNoticeMessage(self, user: "IRCUser", data: Dict[Any, Any]) -> None:
		self.returnMessage("NOTICE", user, data)
	
	def returnMessage(self, command: str, user: "IRCUser", data: Dict[Any, Any]) -> None:
		if "capabilities" not in user.cache or "echo-message" not in user.cache["capabilities"]:
			return
		userPrefix = user.hostmask()
		conditionalTags = {}
		self.ircd.runActionStandard("sendingusertags", user, conditionalTags)
		tags = user.filterConditionalTags(conditionalTags)
		if "targetchans" in data:
			for channel, message in data["targetchans"].items():
				user.sendMessage(command, message, to=channel.name, prefix=userPrefix, tags=tags)
		if "targetusers" in data:
			for targetUser, message in data["targetusers"].items():
				user.sendMessage(command, message, to=targetUser.nick, prefix=userPrefix, tags=tags)

echoMessage = EchoMessage()
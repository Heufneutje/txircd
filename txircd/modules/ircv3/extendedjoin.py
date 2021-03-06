from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData, ModuleData
from zope.interface import implementer
from typing import Callable, List, Optional, Tuple

@implementer(IPlugin, IModuleData)
class ExtendedJoin(ModuleData):
	name = "ExtendedJoin"
	
	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("capabilitylist", 10, self.addCapability),
		         ("joinmessage", 2, self.sendExtJoin) ]
	
	def load(self) -> None:
		if "unloading-extended-join" in self.ircd.dataCache:
			del self.ircd.dataCache["unloading-extended-join"]
			return
		if "cap-add" in self.ircd.functionCache:
			self.ircd.functionCache["cap-add"]("extended-join")
	
	def unload(self) -> Optional["Deferred"]:
		self.ircd.dataCache["unloading-extended-join"] = True
	
	def fullUnload(self) -> Optional["Deferred"]:
		del self.ircd.dataCache["unloading-extended-join"]
		if "cap-del" in self.ircd.functionCache:
			self.ircd.functionCache["cap-del"]("extended-join")
	
	def addCapability(self, user: "IRCUser", capList: List[str]) -> None:
		capList.append("extended-join")
	
	def sendExtJoin(self, messageUsers: List["IRCUser"], channel: "IRCChannel", user: "IRCUser", batchName: str) -> None:
		userPrefix = user.hostmask()
		conditionalTags = {}
		self.ircd.runActionStandard("sendingusertags", user, conditionalTags)
		if user.metadataKeyExists("account"):
			userAccount = user.metadataValue("account")
		else:
			userAccount = "*"
		extJoinUsers = []
		for toUser in messageUsers:
			if "capabilities" in toUser.cache and "extended-join" in toUser.cache["capabilities"]:
				extJoinUsers.append(toUser)
				tags = toUser.filterConditionalTags(conditionalTags)
				if batchName is None:
					toUser.sendMessage("JOIN", userAccount, user.gecos, to=channel.name, prefix=userPrefix, tags=tags)
				else:
					toUser.sendMessageInBatch(batchName, "JOIN", userAccount, user.gecos, to=channel.name, prefix=userPrefix, tags=tags)
		for extUser in extJoinUsers:
			messageUsers.remove(extUser)

extJoin = ExtendedJoin()
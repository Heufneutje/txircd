from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.config import ConfigValidationError
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from txircd.modules.xlinebase import XLineBase
from txircd.utils import durationToSeconds, ircLower, now
from zope.interface import implementer
from fnmatch import fnmatchcase
from typing import Any, Callable, Dict, List, Optional, Tuple

@implementer(IPlugin, IModuleData)
class QLine(ModuleData, XLineBase):
	name = "QLine"
	core = True
	lineType = "Q"
	
	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("register", 10, self.checkLines),
		         ("commandpermission-NICK", 10, self.checkNick),
		         ("commandpermission-QLINE", 10, self.restrictToOper),
		         ("statsruntype-qlines", 10, self.generateInfo),
		         ("xlinetypeallowsexempt", 10, self.qlineNotExempt),
		         ("burst", 10, self.burstLines) ]
	
	def userCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("QLINE", 1, UserQLine(self)) ]
	
	def serverCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("ADDLINE", 1, ServerAddQLine(self)),
		         ("DELLINE", 1, ServerDelQLine(self)) ]
	
	def load(self) -> None:
		self.initializeLineStorage()

	def verifyConfig(self, config: Dict[str, Any]) -> None:
		if "client_ban_msg" in config and not isinstance(config["client_ban_msg"], str):
			raise ConfigValidationError("client_ban_msg", "value must be a string")
	
	def checkUserMatch(self, user: "IRCUser", mask: str, data: Optional[Dict[Any, Any]]) -> bool:
		if data and "newnick" in data:
			return fnmatchcase(ircLower(data["newnick"]), ircLower(mask))
		return fnmatchcase(ircLower(user.nick), ircLower(mask))
	
	def changeNick(self, user: "IRCUser", reason: str, hasBeenConnected: bool) -> None:
		self.ircd.log.info("Matched user {user.uuid} ({user.nick}) against a q:line: {reason}", user=user, reason=reason)
		if hasBeenConnected:
			user.sendMessage("NOTICE", "Your nickname has been changed, as it is now invalid. ({})".format(reason))
		else:
			user.sendMessage("NOTICE", "The nickname you chose was invalid. ({})".format(reason))
		user.changeNick(user.uuid)
	
	def checkLines(self, user: "IRCUser") -> bool:
		reason = self.matchUser(user)
		if reason is not None:
			self.changeNick(user, reason, False)
		return True
	
	def checkNick(self, user: "IRCUser", data: Dict[Any, Any]) -> Optional[bool]:
		self.expireLines()
		newNick = data["nick"]
		reason = self.matchUser(user, { "newnick": newNick })
		if reason is not None:
			user.sendMessage("NOTICE", "The nickname you chose was invalid. ({})".format(reason))
			return False
		return None
	
	def restrictToOper(self, user: "IRCUser", data: Dict[Any, Any]) -> Optional[bool]:
		if not self.ircd.runActionUntilValue("userhasoperpermission", user, "command-qline", users=[user]):
			user.sendMessage(irc.ERR_NOPRIVILEGES, "Permission denied - You do not have the correct operator privileges")
			return False
		return None
	
	def qlineNotExempt(self, lineType: str) -> bool:
		if lineType == "Q":
			return False
		return True

@implementer(ICommand)
class UserQLine(Command):
	def __init__(self, module):
		self.module = module
	
	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		if len(params) < 1 or len(params) == 2:
			user.sendSingleError("QLineParams", irc.ERR_NEEDMOREPARAMS, "QLINE", "Not enough parameters")
			return None
		if len(params) == 1:
			return {
				"mask": params[0]
			}
		return {
			"mask": params[0],
			"duration": durationToSeconds(params[1]),
			"reason": " ".join(params[2:])
		}
	
	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		banmask = data["mask"]
		if "reason" in data:
			if not self.module.addLine(banmask, now(), data["duration"], user.hostmask(), data["reason"]):
				user.sendMessage("NOTICE", "*** Q:Line for {} is already set.".format(banmask))
				return True
			for checkUser in self.module.ircd.users.values():
				reason = self.module.matchUser(checkUser)
				if reason is not None:
					self.module.changeNick(checkUser, reason, True)
			if data["duration"] > 0:
				user.sendMessage("NOTICE", "*** Timed q:line for {} has been set, to expire in {} seconds.".format(banmask, data["duration"]))
			else:
				user.sendMessage("NOTICE", "*** Permanent q:line for {} has been set.".format(banmask))
			return True
		if not self.module.delLine(banmask, user.hostmask()):
			user.sendMessage("NOTICE", "*** Q:Line for {} doesn't exist.".format(banmask))
			return True
		user.sendMessage("NOTICE", "*** Q:Line for {} has been removed.".format(banmask))
		return True

@implementer(ICommand)
class ServerAddQLine(Command):
	def __init__(self, module):
		self.module = module
		self.burstQueuePriority = module.burstQueuePriority
	
	def parseParams(self, server: "IRCServer", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		return self.module.handleServerAddParams(server, params, prefix, tags)
	
	def execute(self, server: "IRCServer", data: Dict[Any, Any]) -> bool:
		if self.module.executeServerAddCommand(server, data):
			for user in self.module.ircd.users.values():
				if not user.isRegistered():
					continue
				reason = self.module.matchUser(user)
				if reason is not None:
					self.module.changeNick(user, reason, True)
			return True
		return False

@implementer(ICommand)
class ServerDelQLine(Command):
	def __init__(self, module):
		self.module = module
		self.burstQueuePriority = module.burstQueuePriority
	
	def parseParams(self, server: "IRCServer", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		return self.module.handleServerDelParams(server, params, prefix, tags)
	
	def execute(self, server: "IRCServer", data: Dict[Any, Any]) -> bool:
		return self.module.executeServerDelCommand(server, data)

qlineModule = QLine()
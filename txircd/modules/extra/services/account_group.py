from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implementer
from typing import Any, Dict, List, Optional, Tuple

irc.ERR_SERVICES = "955" # Custom numeric; 955 <TYPE> <SUBTYPE> <ERROR>

@implementer(IPlugin, IModuleData)
class AccountGroup(ModuleData):
	name = "AccountGroup"
	
	def userCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("ACCOUNTGROUP", 1, CommandGroup(self.ircd)),
			("ACCOUNTUNGROUP", 1, CommandUngroup(self.ircd)) ]

@implementer(ICommand)
class CommandGroup(Command):
	def __init__(self, ircd):
		self.ircd = ircd
	
	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		return {}
	
	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		if not user.metadataKeyExists("account"):
			user.sendMessage(irc.ERR_SERVICES, "ACCOUNT", "GROUP", "NOTLOGIN")
			user.sendMessage("NOTICE", "You're not logged in.")
			return True
		resultValue = self.ircd.runActionUntilValue("accountaddnick", user.metadataValue("account"), user.nick)
		if not resultValue:
			user.sendMessage(irc.ERR_SERVICES, "ACCOUNT", "GROUP", "NOACCOUNT")
			user.sendMessage("NOTICE", "This server doesn't have accounts set up.")
			return True
		if resultValue[0]:
			user.sendMessage("NOTICE", "{} was successfully linked to your account.".format(user.nick))
			return True
		user.sendMessage(irc.ERR_SERVICES, "ACCOUNT", "GROUP", resultValue[1])
		user.sendMessage("NOTICE", "Couldn't group nick: {}".format(resultValue[2]))
		return True

@implementer(ICommand)
class CommandUngroup(Command):
	def __init__(self, ircd):
		self.ircd = ircd
	
	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		if not params:
			user.sendSingleError("UngroupParams", irc.ERR_NEEDMOREPARAMS, "ACCOUNTUNGROUP", "Not enough parameters")
			return None
		return {
			"removenick": params[0]
		}
	
	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		if not user.metadataKeyExists("account"):
			user.sendMessage(irc.ERR_SERVICES, "ACCOUNT", "GROUP", "NOTLOGIN")
			user.sendMessage("NOTICE", "You're not logged in.")
			return True
		removeNick = data["removenick"]
		resultValue = self.ircd.runActionUntilValue("accountremovenick", user.metadataValue("account"), removeNick)
		if not resultValue:
			user.sendMessage(irc.ERR_SERVICES, "ACCOUNT", "GROUP", "NOACCOUNT")
			user.sendMessage("NOTICE", "This server doesn't have accounts set up.")
			return True
		if resultValue[0]:
			user.sendMessage("NOTICE", "{} was successfully removed from your account.".format(removeNick))
			return True
		user.sendMessage(irc.ERR_SERVICES, "ACCOUNT", "GROUP", resultValue[1])
		user.sendMessage("NOTICE", "Couldn't ungroup nick: {}".format(resultValue[2]))
		return True

groupCommand = AccountGroup()
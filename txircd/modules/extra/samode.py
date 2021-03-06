from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import ICommand, IModuleData, Command, ModuleData
from zope.interface import implementer
from typing import Any, Callable, Dict, List, Optional, Tuple

@implementer(IPlugin, IModuleData, ICommand)
class SamodeCommand(ModuleData, Command):
	name = "SamodeCommand"

	def userCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("SAMODE", 1, self) ]

	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("commandpermission-SAMODE", 1, self.restrictToOpers) ]

	def restrictToOpers(self, user: "IRCUser", data: Dict[Any, Any]) -> Optional[bool]:
		if not self.ircd.runActionUntilValue("userhasoperpermission", user, "command-samode", users=[user]):
			user.sendMessage(irc.ERR_NOPRIVILEGES, "Permission denied - You do not have the correct operator privileges")
			return False
		return None

	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		if len(params) < 2:
			user.sendSingleError("SamodeCmd", irc.ERR_NEEDMOREPARAMS, "SAMODE", "Not enough parameters")
			return None
		if params[0] in self.ircd.channels:
			return {
				"targetchannel": self.ircd.channels[params[0]],
				"modes": params[1],
				"params": params[2:]
			}
		if params[0] in self.ircd.userNicks:
			return {
				"targetuser": self.ircd.userNicks[params[0]],
				"modes": params[1],
				"params": params[2:]
			}
		user.sendSingleError("SamodeCmd", irc.ERR_NOSUCHNICK, params[0], "No such nick/channel")
		return None

	def affectedChannels(self, user: "IRCUser", data: Dict[Any, Any]) -> List["IRCChannel"]:
		if "targetchannel" in data:
			return [ data["targetchannel"] ]
		return []

	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		modeStr = data["modes"]
		params = data["params"]
		if "targetchannel" in data:
			channel = data["targetchannel"]
			channel.setModesByUser(user, modeStr, params, True)
			self.ircd.log.info("User {user.uuid} ({user.nick}) forcibly set modes {modeString} on channel {channel.name}", user=user, channel=channel, modeString=("{} {}".format(modeStr, " ".join(params)) if params else modeStr))
		elif "targetuser" in data:
			u = data["targetuser"]
			u.setModesByUser(user, modeStr, params, True)
			self.ircd.log.info("User {user.uuid} ({user.nick}) forcibly set modes {modeString} on user {targetUser.uuid} ({targetUser.nick})", user=user, targetUser=u, modeString=("{} {}".format(modeStr, " ".join(params)) if params else modeStr))
		return True

samode = SamodeCommand()
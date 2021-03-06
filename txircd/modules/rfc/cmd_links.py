from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implementer
from typing import Any, Dict, List, Optional, Tuple

@implementer(IPlugin, IModuleData, ICommand)
class LinksCommand(ModuleData, Command):
	name = "LinksCommand"
	core = True
	
	def userCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("LINKS", 1, self) ]
	
	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		return {}
	
	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		user.sendMessage(irc.RPL_LINKS, self.ircd.name, self.ircd.name, "0 {}".format(self.ircd.config["server_description"]))
		for server in self.ircd.servers.values():
			hopCount = 1
			nextServer = server.nextClosest
			while nextServer != self.ircd.serverID:
				nextServer = self.ircd.servers[nextServer].nextClosest
				hopCount += 1
			if server.nextClosest == self.ircd.serverID:
				nextClosestName = self.ircd.name
			else:
				nextClosestName = self.ircd.servers[server.nextClosest].name
			user.sendMessage(irc.RPL_LINKS, server.name, nextClosestName, "{} {}".format(hopCount, server.description))
		user.sendMessage(irc.RPL_ENDOFLINKS, "*", "End of /LINKS list.")
		return True

linksCmd = LinksCommand()
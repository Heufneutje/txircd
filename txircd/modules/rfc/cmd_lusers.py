from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implementer
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

irc.RPL_LOCALUSERS = "265"
irc.RPL_GLOBALUSERS = "266"

@implementer(IPlugin, IModuleData, ICommand)
class LUsersCommand(ModuleData, Command):
	name = "LUsersCommand"
	core = True
	
	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("welcome", 6, lambda user: self.execute(user, {})) ]
	
	def userCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("LUSERS", 1, self) ]

	def getStorage(self) -> int:
		if "user_count_max" not in self.ircd.storage:
			self.ircd.storage["user_count_max"] = {}
		return self.ircd.storage["user_count_max"]
	
	def updateMaxCounts(self, counts: Dict[str, int]) -> Dict[str, int]:
		maxes = self.getStorage()
		for key in ("users", "local"):
			if counts[key] > maxes.get(key, 0):
				maxes[key] = counts[key]
		return maxes
	
	def countStats(self) -> Tuple[Dict[str, int], Dict[str, int]]:
		counts = defaultdict(lambda: 0)
		counts["users"] = len(self.ircd.users)
		counts["servers"] = len(self.ircd.servers) + 1
		counts["channels"] = len(self.ircd.channels)

		for user in self.ircd.users.values():
			if "i" in user.modes:
				counts["invisible"] += 1
			if "o" in user.modes:
				counts["opers"] += 1
			if user.uuid[:3] == self.ircd.serverID:
				counts["local"] += 1

		for server in self.ircd.servers.values():
			if server.nextClosest == self.ircd.serverID:
				counts["localservers"] += 1

		counts["visible"] = counts["users"] - counts["invisible"]
		maxes = self.updateMaxCounts(counts)
		return counts, maxes
	
	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		return {}
	
	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		counts, maxes = self.countStats()
		user.sendMessage(irc.RPL_LUSERCLIENT, "There are {counts[visible]} users and {counts[invisible]} invisible on {counts[servers]} servers".format(counts=counts))
		user.sendMessage(irc.RPL_LUSEROP, str(counts["opers"]), "operator{} online".format("" if counts["opers"] == 1 else "s"))
		user.sendMessage(irc.RPL_LUSERCHANNELS, str(counts["channels"]), "channel{} formed".format("" if counts["channels"] == 1 else "s"))
		user.sendMessage(irc.RPL_LUSERME, "I have {counts[local]} clients and {counts[localservers]} servers".format(counts=counts))
		user.sendMessage(irc.RPL_LOCALUSERS, "Current Local Users: {}  Max: {}".format(counts["local"], maxes["local"]))
		user.sendMessage(irc.RPL_GLOBALUSERS, "Current Global Users: {}  Max: {}".format(counts["users"], maxes["users"]))
		return True

lusersCmd = LUsersCommand()
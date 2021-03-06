from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from txircd.utils import ipAddressToShow, now, timestampStringFromTimeSeconds
from zope.interface import implementer
from typing import Any, Dict, List, Optional, Tuple

irc.RPL_WHOISHOST = "378"
irc.RPL_WHOISSECURE = "671"

@implementer(IPlugin, IModuleData, ICommand)
class WhoisCommand(ModuleData, Command):
	name = "WhoisCommand"
	core = True
	
	def userCommands(self) -> List[Tuple[str, int, Command]]:
		return [ ("WHOIS", 1, self) ]
	
	def parseParams(self, user: "IRCUser", params: List[str], prefix: str, tags: Dict[str, Optional[str]]) -> Optional[Dict[Any, Any]]:
		if not params:
			user.sendSingleError("WhoisCmd", irc.ERR_NEEDMOREPARAMS, "WHOIS", "Not enough parameters")
			return None
		targetNicks = params[0].split(",")
		targetUsers = []
		for nick in targetNicks:
			if nick not in self.ircd.userNicks:
				user.sendMessage(irc.ERR_NOSUCHNICK, nick, "No such nick")
				continue
			targetUsers.append(self.ircd.userNicks[nick])
		if not targetUsers:
			return None
		return {
			"targetusers": targetUsers
		}
	
	def execute(self, user: "IRCUser", data: Dict[Any, Any]) -> bool:
		for targetUser in data["targetusers"]:
			user.sendMessage(irc.RPL_WHOISUSER, targetUser.nick, targetUser.ident, targetUser.host(), "*", targetUser.gecos)
			if self.ircd.runActionUntilValue("userhasoperpermission", user, "whois-host", users=[user]) or user == targetUser:
				user.sendMessage(irc.RPL_WHOISHOST, targetUser.nick, "is connecting from {}@{} {}".format(targetUser.ident, targetUser.realHost, ipAddressToShow(targetUser.ip)))
			chanList = []
			for channel in targetUser.channels:
				if self.ircd.runActionUntilValue("showchannel-whois", channel, user, targetUser, users=[user, targetUser], channels=[channel]) is not False:
					chanList.append("{}{}".format(self.ircd.runActionUntilValue("channelstatuses", channel, targetUser, user, users=[targetUser, user], channels=[channel]), channel.name))
			if chanList:
				user.sendMessage(irc.RPL_WHOISCHANNELS, targetUser.nick, " ".join(chanList))
			if targetUser.uuid[:3] == self.ircd.serverID:
				serverName = self.ircd.name
				serverDescription = self.ircd.config["server_description"]
			else:
				server = self.ircd.servers[targetUser.uuid[:3]]
				serverName = server.name
				serverDescription = server.description
			user.sendMessage(irc.RPL_WHOISSERVER, targetUser.nick, serverName, serverDescription)
			if self.ircd.runActionUntilValue("userhasoperpermission", targetUser, "", users=[targetUser]):
				user.sendMessage(irc.RPL_WHOISOPERATOR, targetUser.nick, "is an IRC operator")
			if targetUser.secureConnection:
				user.sendMessage(irc.RPL_WHOISSECURE, targetUser.nick, "is using a secure connection")
			self.ircd.runActionStandard("extrawhois", user, targetUser)
			if targetUser.uuid[:3] == self.ircd.serverID: # Idle time will only be accurate for local users
				signonTSString = timestampStringFromTimeSeconds(targetUser.connectedSince)
				idleTime = int((now() - user.idleSince).total_seconds())
				user.sendMessage(irc.RPL_WHOISIDLE, targetUser.nick, str(idleTime), signonTSString, "seconds idle, signon time")
			user.sendMessage(irc.RPL_ENDOFWHOIS, targetUser.nick, "End of /WHOIS list")
		return True

whois = WhoisCommand()
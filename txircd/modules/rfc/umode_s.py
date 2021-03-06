from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import IMode, IModuleData, Mode, ModuleData
from txircd.utils import ircLower, ModeType, timestampStringFromTimeSeconds
from zope.interface import implementer
from typing import Callable, List, Optional, Tuple
from weakref import WeakSet

irc.RPL_LISTMODE = "786" # Made up
irc.RPL_ENDOFLISTMODE = "787" # Made up
irc.ERR_INVALIDSNOTYPE = "985" # Made up, is not used by any IRCd

@implementer(IPlugin, IModuleData, IMode)
class ServerNoticeMode(ModuleData, Mode):
	name = "ServerNoticeMode"
	core = True
	subscribeLists = {}

	def userModes(self) -> List[Tuple[str, ModeType, Mode]]:
		return [ ("s", ModeType.List, self) ]

	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("modepermission-user-s", 1, self.checkModePermission),
		         ("modechange-user-s", 1, self.modeChanged),
		         ("sendservernotice", 1, self.sendServerNotice) ]

	def checkModePermission(self, user: "IRCUser", settingUser: "IRCUser", adding: bool, param: str) -> Optional[bool]:
		if adding:
			if self.ircd.runActionUntilValue("userhasoperpermission", user, "servernotice-{}".format(ircLower(param)), users=[user]):
				return True
			user.sendMessage(irc.ERR_NOPRIVILEGES, "Permission denied - You do not have the correct operator privileges")
			return False
		return None

	def modeChanged(self, user: "IRCUser", source: str, adding: bool, param: str) -> None:
		if adding:
			if param not in self.subscribeLists:
				self.subscribeLists[param] = WeakSet()
			if user.uuid[:3] == self.ircd.serverID:
				self.subscribeLists[param].add(user)
		else:
			if param in self.subscribeLists and user in self.subscribeLists[param]:
				self.subscribeLists[param].remove(user)

	def sendServerNotice(self, mask: str, message: str) -> None:
		if mask in self.subscribeLists:
			message = "*** {}".format(message)
			for u in self.subscribeLists[mask]:
				u.sendMessage("NOTICE", message)

	def checkSet(self, user: "IRCUser", param: str) -> Optional[List[str]]:
		noticeTypes = ircLower(param).split(",")
		badTypes = []
		for noticeType in noticeTypes:
			if not self.ircd.runActionUntilTrue("servernoticetype", user, noticeType):
				user.sendMessage(irc.ERR_INVALIDSNOTYPE, noticeType, "Invalid server notice type")
				badTypes.append(noticeType)
		for noticeType in badTypes:
			noticeTypes.remove(noticeType)
		return noticeTypes

	def checkUnset(self, user: "IRCUser", param: str) -> Optional[List[str]]:
		return ircLower(param).split(",")

	def showListParams(self, user: "IRCUser", target: "IRCUser") -> None:
		if "s" in target.modes:
			for mask in target.modes["s"]:
				target.sendMessage(irc.RPL_LISTMODE, "s", mask[0], mask[1], timestampStringFromTimeSeconds(mask[2]))
		target.sendMessage(irc.RPL_ENDOFLISTMODE, "End of server notice type list")

snoMode = ServerNoticeMode()
from twisted.plugin import IPlugin
from txircd.config import ConfigValidationError
from txircd.module_interface import IModuleData, ModuleData
from zope.interface import implementer
from typing import Any, Callable, Dict, List, Optional, Tuple

@implementer(IPlugin, IModuleData)
class ConnectionLimit(ModuleData):
	name = "ConnectionLimit"
	peerConnections = {}

	def actions(self) -> List[Tuple[str, int, Callable]]:
		return [ ("userconnect", 100, self.handleLocalConnect),
		         ("remoteregister", 100, self.handleRemoteConnect),
		         ("quit", 100, self.handleDisconnect),
		         ("remotequit", 100, self.handleDisconnect) ]

	def load(self) -> None:
		for user in self.ircd.users.values():
			self.addToConnections(user.ip)

	def verifyConfig(self, config: Dict[str, Any]) -> None:
		if "connlimit_globmax" in config and (not isinstance(config["connlimit_globmax"], int) or config["connlimit_globmax"] < 0):
			raise ConfigValidationError("connlimit_globmax", "invalid number")
		if "connlimit_whitelist" in config:
			if not isinstance(config["connlimit_whitelist"], list):
				raise ConfigValidationError("connlimit_whitelist", "value must be a list")
			for ip in config["connlimit_whitelist"]:
				if not isinstance(ip, str):
					raise ConfigValidationError("connlimit_whitelist", "every entry must be a valid ip")

	def handleLocalConnect(self, user: "IRCUser", *params: Any) -> Optional[bool]:
		ip = user.ip
		if self.addToConnections(ip) and self.peerConnections[ip] > self.ircd.config.get("connlimit_globmax", 3):
			self.ircd.log.info("Connection limit reached from {ip}", ip=ip)
			user.disconnect("No more connections allowed from your IP ({})".format(ip))
			return None
		return True

	def handleRemoteConnect(self, user: "IRCUser", *params: Any) -> None:
		self.addToConnections(user.ip)

	def handleDisconnect(self, user: "IRCUser", *params: Any) -> None:
		ip = user.ip
		if ip in self.peerConnections:
			self.peerConnections[ip] -= 1
			if self.peerConnections[ip] < 1:
				del self.peerConnections[ip]

	def addToConnections(self, ip: str) -> bool:
		if ip in self.ircd.config.get("connlimit_whitelist", []):
			return False
		if ip in self.peerConnections:
			self.peerConnections[ip] += 1
		else:
			self.peerConnections[ip] = 1
		return True

connLimit = ConnectionLimit()
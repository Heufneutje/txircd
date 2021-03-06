from twisted.conch.manhole_tap import makeService
from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData, ModuleData
from zope.interface import implementer
from typing import Any, Optional

@implementer(IPlugin, IModuleData)
class Manhole(ModuleData):
	name = "Manhole"
	
	manhole = None
	deferredStop = None
	
	def load(self) -> None:
		self.startManhole()
	
	def unload(self) -> Optional["Deferred"]:
		if self.deferredStop and not self.deferredStop.called:
			self.deferredStop.addCallback(lambda result: self.manhole.stopService())
			return self.deferredStop
		return self.manhole.stopService()
	
	def rehash(self) -> None:
		if self.deferredStop and not self.deferredStop.called:
			return # The deferred's callbacks should handle the rest of the rehash
		d = self.manhole.stopService()
		if d:
			d.addCallback(self.startManhole)
			self.deferredStop = d
		else:
			self.startManhole()
	
	def startManhole(self, result: Any = None) -> None:
		self.manhole = makeService({
			"namespace": { "ircd": self.ircd },
			"passwd": self.ircd.config.get("manhole_passwd", "manhole.passwd"),
			"telnetPort": self.ircd.config.get("manhole_bind_telnet", None),
			"sshPort": self.ircd.config.get("manhole_bind_ssh", None)
		})
		self.manhole.startService()

manhole = Manhole()
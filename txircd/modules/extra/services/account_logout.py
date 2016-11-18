from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implements

class AccountLogout(ModuleData, Command):
	implements(IPlugin, IModuleData, ICommand)
	
	name = "AccountLogout"
	
	def userCommands(self):
		return [ ("LOGOUT", 1, self) ]
	
	def parseParams(self, user, params, prefix, tags):
		return {}
	
	def execute(self, user, data):
		if not user.metadataExists("account"):
			user.sendMessage(irc.ERR_SERVICES, "ACCOUNT", "LOGOUT", "You're not logged in")
			user.sendMessage("NOTICE", "You're not logged in.")
			return True
		self.ircd.runActionStandard("accountlogout", user)
		user.sendMessage("NOTICE", "You are now logged out.")
		return True

logoutCommand = AccountLogout()
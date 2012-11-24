# The purpose of this file is to provide base classes with the needed functions
# already defined; this allows us to guarantee that any exceptions raised
# during function calls are a problem with the module and not just that the
# particular function isn't defined.

class Module(object):
	def hook(self, base):
		self.ircd = base
		return self

class Mode(object):
	def hook(self, base):
		self.ircd = base
		return self
	def prefixSymbol(self):
		return None
	def checkSet(self, channel, param):
		return True
	def checkUnset(self, channel, param):
		return True
	def onJoin(self, channel, user, params):
		return "pass"
	def checkPermission(self, user, cmd, params):
		return "pass"
	def onMessage(self, sender, target, message):
		return ["pass"]
	def onPart(self, channel, user, reason):
		pass
	def onTopicChange(self, channel, user, topic):
		pass
	def commandData(self, command, *args):
		pass

def Command(object):
	def hook(self, base):
		self.ircd = base
		return self
	def onUse(self, user, params):
		pass
	def processParams(self, user, params):
		return [ "cu", {
			"user": user,
			"params": params
		} ]
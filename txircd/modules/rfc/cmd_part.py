from twisted.plugin import IPlugin
from twisted.words.protocols import irc
from txircd.module_interface import Command, ICommand, IModuleData, ModuleData
from zope.interface import implements

class PartCommand(ModuleData):
    implements(IPlugin, IModuleData)
    
    name = "PartCommand"
    core = True
    
    def hookIRCd(self, ircd):
        self.ircd = ircd
    
    def actions(self):
        return [ ("partmessage", 1, self.sendPartMessage) ]
    
    def userCommands(self):
        return [ ("PART", 1, UserPart(self.ircd)) ]
    
    def serverCommands(self):
        return [ ("PART", 1, ServerPart(self.ircd)) ]
    
    def sendPartMessage(self, channel, user, reason, sendUserList):
        userHostmask = user.hostmask()
        reason = ":{}".format(reason)
        for destUser in sendUserList:
            destUser.sendMessage("PART", channel.name, reason, prefix=userHostmask)
        del sendUserList[:]

class UserPart(Command):
    implements(ICommand)
    
    def __init__(self, ircd):
        self.ircd = ircd
    
    def parseParams(self, user, params, prefix, tags):
        if not params or not params[0]:
            user.sendMessage(irc.ERR_NEEDMOREPARAMS, "PART", ":Not enough parameters")
            return None
        if params[0] not in self.ircd.channels:
            user.sendMessage(irc.ERR_NOSUCHCHANNEL, params[0], ":No such channel")
            return None
        reason = params[1] if len(params) > 1 else ""
        reason = reason[:self.ircd.config.getWithDefault("part_message_length", 300)]
        return {
            "channel": self.ircd.channels[params[0]],
            "reason": reason
        }
    
    def execute(self, user, data):
        channel = data["channel"]
        reason = data["reason"]
        if "partmessage" in self.ircd.actions:
            sendUserList = channel.users.keys()
            for action in self.ircd.actions["partmessage"]:
                action[0](channel, user, reason, sendUserList)
                if not sendUserList:
                    break
        user.leaveChannel(channel)
        return True

class ServerPart(Command):
    implements(ICommand)
    
    def __init__(self, ircd):
        self.ircd = ircd
    
    def parseParams(self, server, params, prefix, tags):
        if len(params) != 2 or not params[0]:
            return None
        if prefix not in self.ircd.users:
            return None
        if params[0] not in self.ircd.channels:
            return None
        return {
            "user": self.ircd.users[prefix],
            "channel": self.ircd.channels[params[0]],
            "reason": params[1]
        }
    
    def execute(self, server, data):
        user = data["user"]
        channel = data["channel"]
        reason = data["reason"]
        if "partmessage" in self.ircd.actions:
            sendUserList = [u for u in channel.users.iterkeys() if u.uuid[:3] == self.ircd.serverID]
            for action in self.ircd.actions["partmessage"]:
                action[0](channel, user, reason, sendUserList)
                if not sendUserList:
                    break
        user.leaveChannel(channel, True)
        return True

partCommand = PartCommand()
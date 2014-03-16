from txircd.utils import ModeType, now

class IRCChannel(object):
    def __init__(self, ircd, name):
        self.ircd = ircd
        self.name = name
        self.users = {}
        self.modes = {}
        self.topic = ""
        self.topicSetter = ""
        self.topicTime = now()
        self.metadata = {
            "server": {},
            "user": {},
            "client": {},
            "ext": {},
            "private": {}
        }
        self.cache = {}
    
    def sendMessage(self, command, *params, **kw):
        if "to" not in kw:
            kw["to"] = self.name
        if kw["to"] is None:
            del kw["to"]
        userList = self.users.keys()
        if "skip" in kw:
            for u in kw["skip"]:
                userList.remove(u)
        servers = set()
        for user in self.users.iterkeys():
            if user.uuid[:3] != self.ircd.serverID:
                servers.add(user.uuid[:3])
        self.ircd.runActionProcessingMultiple("sendchannelmessage-{}".format(command), (users, servers), self, *params, **kw)
        if users or servers:
            self.ircd.runActionProcessingMultiple("sendchannelmessage", (users, servers), self, command, *params, **kw)
    
    def setTopic(self, topic, setter):
        oldTopic = self.topic
        self.topic = topic
        self.topicSetter = setter
        self.topicTime = now()
        self.ircd.runActionStandard("topic", self, oldTopic)
    
    def setMetadata(self, namespace, key, value = None):
        if namespace not in self.metadata:
            return
        oldValue = None
        if key in self.metadata[namespace]:
            oldValue = self.metadata[namespace][key]
        if oldValue == value:
            return
        if value is None:
            del self.metadata[namespace][key]
        else:
            self.metadata[namespace][key] = value
        self.ircd.runActionStandard("channelmetadataupdate", self, namespace, key, value)
    
    def setModes(self, user, modeString, params, source = None):
        adding = True
        changing = []
        for mode in modeString:
            if len(changing) >= 20:
                break
            if mode == "+":
                adding = True
                continue
            if mode == "-":
                adding = False
                continue
            if mode not in self.ircd.channelModeTypes:
                if user:
                    user.sendMessage(irc.ERR_UNKNOWNMODE, mode, ":is unknown mode char to me")
                continue
            modeType = self.ircd.channelModeTypes[mode]
            param = None
            if modeType in (ModeType.List, ModeType.ParamOnUnset, ModeType.Status) or (modeType == ModeType.Param and adding):
                try:
                    param = params.pop(0)
                except KeyError:
                    continue
            paramList = [None]
            if modeType == ModeType.Status:
                if adding:
                    paramList = self.ircd.channelStatuses[mode][2].checkSet(param)
                else:
                    paramList = self.ircd.channelStatuses[mode][2].checkUnset(param)
            else:
                if adding:
                    paramList = self.ircd.channelModes[modeType][mode].checkSet(param)
                else:
                    paramList = self.ircd.channelModes[modeType][mode].checkUnset(param)
            if paramList is None:
                continue
            del param
            
            if user:
                source = None
            
            for param in paramList:
                if len(changing) >= 20:
                    break
                if self.ircd.runActionVoting("modepermission-channel-{}".format(mode), self, user, mode, param) < 0:
                    continue
                if adding:
                    if modeType == ModeType.Status:
                        try:
                            user = self.ircd.users[self.ircd.userNicks[param]]
                        except KeyError:
                            continue
                        if user not in self.users:
                            continue
                        if mode in self.users[user]:
                            continue
                        statusLevel = self.ircd.channelStatuses[mode][1]
                        for index, rank in enumerate(self.users[user]):
                            if self.ircd.channelStatuses[rank][1] < statusLevel:
                                self.users[user].insert(index, mode)
                                break
                        else:
                            self.users[user].append(mode)
                    elif modeType == ModeType.List:
                        if mode not in self.modes:
                            self.modes[mode] = []
                        found = False
                        for paramData in self.modes[mode]:
                            if param == paramData[0]:
                                found = True
                                break
                        if found:
                            continue
                        self.modes[mode].append((param, user, source, now()))
                    else:
                        if mode in self.modes and param == self.modes[mode]:
                            continue
                        self.modes[mode] = param
                else:
                    if modeType == ModeType.Status:
                        try:
                            user = self.ircd.users[self.ircd.userNicks[user]]
                            self.users[user].remove(mode)
                        except KeyError, ValueError:
                            continue
                    elif modeType == ModeType.List:
                        if mode not in self.modes:
                            continue
                        for index, paramData in self.modes[mode]:
                            if paramData[0] == param:
                                del self.modes[mode][index]
                                break
                        else:
                            continue
                        if not self.modes[mode]:
                            del self.modes[mode]
                    else:
                        if mode not in self.modes:
                            continue
                        del self.modes[mode]
                changing.append((adding, mode, param, user, source))
                self.ircd.runActionStandard("modechange-channel-{}".format(mode), self, adding, mode, param, user, source)
        if changing:
            changingDisplay = copy(changing)
            self.ircd.runActionProcessing("modemessage-channel", self, changingDisplay)
            self.ircd.runActionStandard("modechanges-channel", self, changing)
        return changing
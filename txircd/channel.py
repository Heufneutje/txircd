from txircd.utils import ModeType, now

class IRCChannel(object):
    def __init__(self, ircd, name):
        self.ircd = ircd
        self.name = name[:64]
        self.users = {}
        self.modes = {}
        self.existedSince = now()
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
        if "skipusers" in kw:
            for u in kw["skipusers"]:
                userList.remove(u)
        servers = set()
        for user in self.users.iterkeys():
            if user.uuid[:3] != self.ircd.serverID:
                servers.add(self.ircd.servers[user.uuid[:3]])
        if "skipservers" in kw:
            for s in kw["skipservers"]:
                servers.discard(s)
        servers = list(servers)
        self.ircd.runActionProcessingMultiple("sendchannelmessage-{}".format(command), (userList, servers), self, *params, **kw)
        if userList or servers:
            self.ircd.runActionProcessingMultiple("sendchannelmessage", (userList, servers), self, command, *params, **kw)
    
    def setTopic(self, topic, setter):
        if setter in self.ircd.users:
            source = self.ircd.users[setter].hostmask()
        elif setter == self.ircd.serverID:
            source = self.ircd.name
        elif setter in self.ircd.servers:
            source = self.ircd.servers[setter].name
        else:
            return False
        oldTopic = self.topic
        self.topic = topic
        self.topicSetter = source
        self.topicTime = now()
        self.ircd.runActionStandard("topic", self, setter, oldTopic)
        return True
    
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
    
    def setModes(self, source, modeString, params):
        adding = True
        changing = []
        user = None
        if source in self.ircd.users:
            user = self.ircd.users[source]
            sourceName = user.hostmask()
        elif source == self.ircd.serverID:
            sourceName = self.ircd.name
        elif source in self.ircd.servers:
            sourceName = self.ircd.servers[source].name
        else:
            raise ValueError ("Source must be a valid user or server ID.")
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
                    if modeType == ModeType.List and user:
                        self.channelModes[modeType][mode].showListParams(user, self)
                    continue
            paramList = [param]
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
            
            for param in paramList:
                if len(changing) >= 20:
                    break
                if user and self.ircd.runActionVoting("modepermission-channel-{}".format(mode), self, user, mode, param) < 0:
                    continue
                if adding:
                    if modeType == ModeType.Status:
                        try:
                            targetUser = self.ircd.users[self.ircd.userNicks[param]]
                        except KeyError:
                            continue
                        if targetUser not in self.users:
                            continue
                        if mode in self.users[targetUser]:
                            continue
                        statusLevel = self.ircd.channelStatuses[mode][1]
                        for index, rank in enumerate(self.users[targetUser]):
                            if self.ircd.channelStatuses[rank][1] < statusLevel:
                                self.users[targetUser].insert(index, mode)
                                break
                        else:
                            self.users[targetUser].append(mode)
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
                        if len(param) > 250: # Set a max limit on param length
                            continue
                        if len(self.modes[mode]) > self.ircd.config.getWithDefault("channel_list_limit", 100):
                            if user:
                                user.sendMessage(irc.ERR_BANLISTFULL, self.name, param, ":Channel +{} list is full".format(mode))
                            continue
                        self.modes[mode].append((param, sourceName, now()))
                    else:
                        if mode in self.modes and param == self.modes[mode]:
                            continue
                        self.modes[mode] = param
                else:
                    if modeType == ModeType.Status:
                        try:
                            targetUser = self.ircd.users[self.ircd.userNicks[param]]
                            self.users[targetUser].remove(mode)
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
                changing.append((adding, mode, param))
                self.ircd.runActionStandard("modechange-channel-{}".format(mode), self, source, adding, mode, param)
        if changing:
            users = []
            for chanUser in self.users.iterkeys():
                if chanUser.uuid[:3] == self.ircd.serverID:
                    users.append(chanUser)
            self.ircd.runActionProcessing("modemessage-channel", users, self, source, sourceName, changing)
            self.ircd.runActionStandard("modechanges-channel", self, source, sourceName, changing)
        return changing
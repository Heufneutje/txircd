from twisted.plugin import IPlugin
from txircd.module_interface import IModuleData, ModuleData
from zope.interface import implementer
from base64 import b64encode, b64decode
try: # The PBKDF2 module is dumb and reacts differently in the presence of PyCrypto, so let's handle its presence appropriately
	from Crypto.Hash import MD5 as md5, SHA as sha1, SHA224 as sha224, SHA256 as sha256, SHA384 as sha384, SHA512 as sha512
except ImportError: # PyCrypto isn't actually present, so let's hashlib
	from hashlib import md5, sha1, sha224, sha256, sha384, sha512
from pbkdf2 import PBKDF2
from random import randint
from struct import pack
from typing import Optional

@implementer(IPlugin, IModuleData)
class HashPBKDF2(ModuleData):
	name = "HashPBKDF2"
	
	def load(self) -> None:
		self.ircd.functionCache["hash-pbkdf2"] = self.hash
		self.ircd.functionCache["compare-pbkdf2"] = self.compare
		self.ircd.functionCache["validate-pbkdf2"] = self.checkValidHash
	
	def unload(self) -> Optional["Deferred"]:
		if self.ircd.functionCache["hash-pbkdf2"] == self.hash:
			del self.ircd.functionCache["hash-pbkdf2"]
		if self.ircd.functionCache["compare-pbkdf2"] == self.compare:
			del self.ircd.functionCache["compare-pbkdf2"]
		if self.ircd.functionCache["validate-pbkdf2"]:
			del self.ircd.functionCache["validate-pbkdf2"]
	
	def hash(self, string: str, salt: str = None, iterations: int = 1000, algorithm: str = "sha256", dataBytes: int = 24) -> str:
		possibleAlgorithms = {
			"md5": md5,
			"sha1": sha1,
			"sha224": sha224,
			"sha256": sha256,
			"sha384": sha384,
			"sha512": sha512
		}
		
		if algorithm not in possibleAlgorithms:
			raise ValueError ("Unknown algorithm {}".format(algorithm))
		
		if iterations < 1:
			raise ValueError ("Invalid iteration count: {}".format(iterations))
		
		if salt is None:
			salt = self.makeSalt()
		
		string = string.encode("utf-8")
		
		saltGoodChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/="
		for char in salt:
			if char not in saltGoodChars:
				raise ValueError ("Illegal character {!r} found in salt".format(char))
		
		hashedStr = b64encode(PBKDF2(string, salt, iterations, possibleAlgorithms[algorithm]).read(dataBytes)).decode("us-ascii")
		return "{}:{}:{}:{}".format(algorithm, iterations, salt, hashedStr)
	
	def makeSalt(self) -> str:
		return b64encode(b"".join([pack("@H", randint(0, 0xffff)) for i in range(3)])).decode("us-ascii")
	
	def compare(self, string: str, compareWith: str) -> bool:
		if not self.checkValidHash(compareWith):
			return False
		# The algorithm outputs strings with all the parameters
		# So we'll pull them apart and feed them to the hash function
		# to make sure the string we're comparing gets hashed the same way
		algorithm, iterations, salt, oldHash = compareWith.split(":", 3)
		if iterations:
			iterations = int(iterations)
		dataBytes = len(b64decode(oldHash))
		
		return self.hash(string, salt, iterations, algorithm, dataBytes) == compareWith
	
	def checkValidHash(self, string: str) -> bool:
		if len(string.split(":")) != 4:
			return False
		algorithm, iterations, salt, hashedString = string.split(":")
		if algorithm not in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512"):
			return False
		try:
			int(iterations)
		except ValueError:
			return False
		return True

pbkdf2Hash = HashPBKDF2()
import os
from twisted.internet import protocol,reactor

spawnMonoProcess(protocol, name, args):
	if os.name == 'nt':
		return reactor.spawnProcess(protocol, name, args)
	else:
		return reactor.spawnProcess(protocol, "mono", name + args)

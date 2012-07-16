import argparse
import ConfigParser
import sys

class Configuration(object):
	def __init__(self, port, dbfile):
		self.port = port
		self.dbfile = dbfile

class ConfigurationLoader(object):
	def __init__(self):

		parser = argparse.ArgumentParser(description="GridToGo Coordination Server")
		parser.add_argument("-c", "--config")
		parser.add_argument("-d", "--database")
		parser.add_argument("-p", "--port")
		self.args = parser.parse_args(sys.argv[1:])
		
		self.configfile = "/etc/gridtogoserver.conf"
		if not self.args.config is None:
			self.configfile = self.args.config

	def load(self):
		configparser = ConfigParser.RawConfigParser()
		configparser.read("gridtogoserver.conf")
		
		conf = Configuration(port = 8017, dbfile = "gridtogoserver.db")

		if configparser.has_option("core", "port"):
			conf.port = configparser.getint("core", "port")
		if configparser.has_option("database", "location"):
			conf.dbfile = configparser.get("database", "location")

		if not self.args.port is None:
			conf.port = int(self.args.port)
		if not self.args.database is None:
			conf.dbfile = self.args.database

		return conf

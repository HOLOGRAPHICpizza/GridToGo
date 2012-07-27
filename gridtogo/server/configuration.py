import argparse
import ConfigParser
import sys

class Configuration(object):
	def __init__(self, port, dbfile, dbtype="sqlite", dbhost="localhost", dbport=27017, dbdatabase="opensim", dbauth=False, dbuser=None, dbpass=None):
		self.port = port
		self.dbfile = dbfile
		self.dbtype = dbtype
		self.dbhost = dbhost
		self.dbport = dbport
		self.dbdatabase = dbdatabase
		self.dbauth = dbauth
		self.dbuser = dbuser
		self.dbpass = dbpass

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
		if configparser.has_option("database", "type"):
			conf.dbtype = configparser.get("database", "type")
		if configparser.has_option("sqlite", "location"):
			conf.dbfile = configparser.get("sqlite", "location")
		if configparser.has_option("mongo", "host"):
			conf.dbhost = configparser.get("mongo", "host")
		if configparser.has_option("mongo", "port"):
			conf.dbport = int(configparser.get("mongo", "port"))
		if configparser.has_option("mongo", "database"):
			conf.dbdatabase = configparser.get("mongo", "database")
		if configparser.has_option("mongo", "auth"):
			conf.dbauth = bool(configparser.get("mongo", "auth"))
		if configparser.has_option("mongo", "user"):
			conf.dbuser = configparser.get("mongo", "user")
		if configparser.has_option("mongo", "pass"):
			conf.dbpass = configparser.get("mongo", "pass")

		if not self.args.port is None:
			conf.port = int(self.args.port)
		if not self.args.database is None:
			conf.dbfile = self.args.database

		return conf

from zope.interface import implements, Interface
import uuid
import sqlite3
from gridtogo.shared.networkobjects import *
from gridtogo.server.configuration import ConfigurationLoader
import sys
from twisted.python import log

try:
	from pymongo import Connection
	havePyMongo = True
except Exception:
	havePyMongo = False
	

class UserAccount(object):
	def __init__(self, UUID, firstName, lastName, hashedPassword, email):
		# UUID is inherently unique and should be used for lookups whenever possible
		# UUID should be an instance of the UUID class
		self.UUID = UUID

		# Names are "soft unique". The new account creation method must check for conflicts!
		self.firstName = firstName
		self.lastName = lastName

		self.hashedPassword = hashedPassword
		self.email = email

	def getUser(self):
		"""Return a full User object created from this UserAccount."""
		user = User()
		user.UUID = self.UUID
		user.firstName = self.firstName
		user.lastName = self.lastName
		user.online = False
		user.NATStatus = False
		return user

class DatabaseException(Exception):
	"""Thrown on a problem with the database."""
	pass

class IDatabase(Interface):
	"""
	Interface for accessing the server database.
	connect should set up initial database structure if necessary.
	All methods, except  __init__() may throw a DatabaseException upon encountering problems.
	"""

	def connect(self, config):
		""" Set up connection to the database """
		pass

	def getUserAccountByName(self, firstName, lastName):
		"""Returns None if no user found."""
		pass

	def storeUserAccount(self, userAccount):
		"""Create or update the record for the given UserAccount object."""
		pass

	def storeGridAssociation(self, user, gridName):
		"""Create or update the association of this User object to this grid."""
		pass

	def getGridUsers(self, gridName):
		"""Return a dictionary of User objects which are members of the given grid name, keys are UUIDs."""
		pass

	#TODO: Possibly make this work like the other "store" functions, update existing entries
	def createRegion(self, gridName, regionName, userUuid):
		"""Creates a region with the specified regionName referencing the specified name and gives the user a regionHost association with the grid"""
		pass
	
	def getGridRegions(self, gridName):
		"""Returns a dictionary of Region Name -> Region where all regions are in the specified grid"""
		pass

	def close(self):
		"""Commits all database changes and releases all resources, if applicable."""
		pass

class SQLiteDatabase(object):
	implements(IDatabase)

	def __init__(self):
		pass
	
	def connect(self, config):
		try:
			self.connection = sqlite3.connect(config.dbfile)
		except sqlite3.Error as e:
			raise DatabaseException(e)

		# create initial structure if necessary
		cursor = self.connection.cursor()
		#TODO: Create SQLite indices for name to optimize retrieval.
		cursor.execute('CREATE TABLE IF NOT EXISTS users(' +
		               'UUID CHAR(36) PRIMARY KEY NOT NULL,' +
		               'firstName VARCHAR(64) NOT NULL,' +
		               'lastName VARCHAR(64) NOT NULL,' +
		               'hashedPassword VARCHAR(64) NOT NULL,' +
		               'email VARCHAR(64) NOT NULL' +
		               ')')

		cursor.execute('CREATE TABLE IF NOT EXISTS grids(' +
		               'name VARCHAR(64) PRIMARY KEY NOT NULL'
		               ')')

		# Regions
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS regions(
				name VARCHAR(64) NOT NULL,
				grid VARCHAR(64) NOT NULL,
				location VARCHAR(64) NOT NULL,
				FOREIGN KEY(grid) REFERENCES grids(name),
				UNIQUE (name, grid, location)
			)
		""")

		# connects user accounts to grids
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS gridUsers(
		        gridName VARCHAR(64) NOT NULL,
				user CHAR(36) NOT NULL,
				moderator BOOLEAN NOT NULL,
				gridHost BOOLEAN NOT NULL,
				FOREIGN KEY(gridName) REFERENCES grids(name),
				FOREIGN KEY(user) REFERENCES users(UUID),
				UNIQUE (gridName, user)
		    )
		""")

		# connects user accounts to regions
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS regionHosts(
				regionName VARCHAR(64) NOT NULL,
				user CHAR(36) NOT NULL,
				FOREIGN KEY(regionName) REFERENCES regions(name),
				FOREIGN KEY(user) REFERENCES users(UUID),
				UNIQUE (regionName, user)
			)
		""")

	def getGridRegions(self, gridName):
		cursor = self.connection.cursor()
		cursor.execute("""
			SELECT name, location
			FROM regions
			WHERE grid=?
		""", gridName)

		regions = {}
		for row in cursor.fetchall():
			region = Region(row[0], row[1], None, None)
			regions[row[0]] = region
		return regions

	def createRegion(self, gridName, regionName, userUuid):
		cursor = self.connection.cursor()

		cursor.execute("""
			INSERT INTO regions VALUES (?,?)
		""", (regionName, gridName))

		cursor.execute("""
			INSERT INTO regionHosts VALUES (?,?)
		""", (regionName, str(userUuid)))

		self.connection.commit()

	def getUserAccountByName(self, firstName, lastName):
		cursor = self.connection.cursor()
		cursor.execute('SELECT * FROM users WHERE firstName=? AND lastName=?', (firstName, lastName))
		row = cursor.fetchone()
		if row is None:
			return None
		return UserAccount(uuid.UUID(row[0]), row[1], row[2], row[3], row[4])

	def storeUserAccount(self, userAccount):
		cursor = self.connection.cursor()
		cursor.execute('INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)',
			(str(userAccount.UUID),
			userAccount.firstName,
			userAccount.lastName,
			userAccount.hashedPassword,
			userAccount.email))
		self.connection.commit()

	def storeGridAssociation(self, user, gridName):
		data = {'gridName': gridName, 'UUID': str(user.UUID), 'moderator': None, 'gridHost': None}

		if hasattr(user, 'moderator'):
			data['moderator'] = user.moderator
		if hasattr(user, 'gridHost'):
			data['gridHost'] = user.gridHost

		cursor = self.connection.cursor()
		cursor.execute("""
			INSERT OR REPLACE INTO gridUsers VALUES (
				:gridName,
				:UUID,
				COALESCE(:moderator, (SELECT moderator FROM gridUsers WHERE gridName=:gridName AND user=:UUID), 0),
				COALESCE(:gridHost, (SELECT gridHost FROM gridUsers WHERE gridName=:gridName AND user=:UUID), 0)
			)
		""", data)
		self.connection.commit()

	def getGridUsers(self, gridName):
		cursor = self.connection.cursor()
		cursor.execute('SELECT users.UUID, users.firstName, users.lastName, gridUsers.moderator, gridUsers.gridHost ' +
		               'FROM users INNER JOIN gridUsers ON users.UUID=gridUsers.user WHERE gridUsers.gridName=?', [gridName])

		users = {}
		for record in cursor.fetchall():
			user = User(uuid.UUID(record[0]), record[1], record[2], False,
						False, bool(record[3]), bool(record[4]), False)
			users[user.UUID] = user
		return users

	def close(self):
		if self.connection:
			self.connection.commit()
			self.connection.close()

class MongoDatabase(object):
	implements(IDatabase)
	def __init__(self):
		if not havePyMongo:
			log.err("Tried to use Mongo without PyMongo")
	
	def connect(self, config):
		log.msg("Initiating Mongo Connection: " + config.dbhost + ":" + str(config.dbport))
		self.connection = Connection(config.dbhost, config.dbport)
		log.msg("Initiated Mongo Connection.")
		log.msg("Using database: " + config.dbdatabase)
		self.database = self.connection[config.dbdatabase]
		if config.dbauth:
			log.msg("Logging into Mongo as " + config.dbuser)
			self.database.authenticate(config.dbuser, config.dbpass)

		log.msg("Ensuring indexes on user: uuid [unique], first_name, last_name")
		self.database['user'].ensure_index("uuid", unique=True)
		self.database['user'].ensure_index("first_name")
		self.database['user'].ensure_index("last_name")
		log.msg("Ensuring index on grid: name [unique]")
		self.database['grid'].ensure_index('name', unique=True)
		log.msg("Ensuring index on region: name")
		self.database['region'].ensure_index('name')
	
	def getUserAccountByName(self, firstName, lastName):
		result = self.database['user'].find_one(
			{"first_name": firstName,
			 "last_name": lastName})
		if result is None:
			return result
		return UserAccount(uuid.UUID(result['uuid']), result['first_name'],
						   result['last_name'], result['hashed_password'],
						   result['email'])

	def storeUserAccount(self, user):
		collection = self.database['user']
		existingAccount = collection.find_one({'uuid': str(user.UUID)})
		userData = {'uuid': str(user.UUID),
					'first_name': user.firstName,
					'last_name': user.lastName,
					'hashed_password': user.hashedPassword,
					'email': user.email }
		if not existingAccount is None:
			userData['_id'] = existingAccount['_id']
		
		collection.save(userData)

	def storeGridAssociation(self, user, gridName):
		userid = self.database['user'].find_one({'uuid': str(user.UUID)})['_id']
		grid = self.database['grid'].find_one({'name': gridName})
		gridid = None
		# TODO Make this less hacky (the grid should actually have to preexist)
		if not grid is None:
			gridid = grid['_id']
		else:
			gridid = self.database['grid'].insert({"name": gridName})
		existingAssoc = self.database['grid_user'].find_one(
			{'grid': gridid,
			 'user': userid
			})
		data = {'grid': gridid, 'user': userid, 'moderator': False, 'grid_host': False}

		if hasattr(user, 'moderator'):
			data['moderator'] = user.moderator
		if hasattr(user, 'gridHost'):
			data['grid_host'] = user.gridHost
		pass

		if not existingAssoc is None:
			data['_id'] = existingAssoc['_id']
		self.database['grid_user'].save(data)

	def getGridUsers(self, gridName):
		gridid = self.database['grid'].find_one({'name': gridName})
		gridNameAssociations = self.database['grid_user'].find(
			{'grid': gridid})
		result = {}
		for gridNameAssoc in gridNameAssociations:
			# This is bad from an efficiency standpoint
			# TODO refactor "schema"
			u = self.database['user'].find_one(
				{'_id': gridNameAssoc['user']})
			user = User(uuid.UUID(u['uuid']), u['first_name'], u['last_name'],
						False, False, gridNameAssoc['moderator'],
						gridNameAssoc['grid_host'], False)

			result[user.UUID] = user
		
		return result
	
	def createRegion(self, gridName, regionName, loc, ehost, uuid):
		userid = self.database['user'].find_one({"uuid": str(uuid)})["_id"]
		gridid = self.database['grid'].find_one({"name": gridName})["_id"]
		regionid = self.database['region'].insert(
			{"name": regionName,
			 "grid": gridid,
			 "location": loc,
			 "external_host": ehost})
		self.database['region_host'].insert(
			{"user": userid,
			 "region": regionid})
	
	def getGridRegions(self, gridName):
		grid = self.database['grid'].find_one({"name": gridName})
		if grid is None:
			return {}
		gridid = grid["_id"]
		regions = self.database['region'].find({"grid":gridid})
		result = {}

		for r in regions:
			# The None is that it is not currently being hosted.
			result[r['name']] = Region(r['name'], r['location'], r['external_host'], None)

		return result

	def close(self):
		self.connection.close()


if __name__ == "__main__":
	log.startLogging(sys.stdout)
	configloader = ConfigurationLoader()
	config = configloader.load()
	if config.dbtype == "sqlite":
		db = IDatabase(SQLiteDatabase())
	elif config.dbtype == "mongo":
		db = IDatabase(MongoDatabase())
	db.connect(config)

	import authentication
	auth = authentication.Authenticator(db)
	request = CreateUserRequest('generated', 'user', 'testpass', 'bademail')
	auth.createUser(request)

	account = db.getUserAccountByName('generated', 'user')
	user = User(account.UUID)
	user.gridHost = True
	db.storeGridAssociation(user, 'testgrid')
	users = db.getGridUsers('testgrid')
	db.close()

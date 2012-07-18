from zope.interface import implements, Interface
import uuid
import sqlite3
from gridtogo.shared.networkobjects import *

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

class Grid(object):

	def __init__(self, name):
		self.name = name

		# list of User objects
		self.users = []

		self.regions = []

class DatabaseException(Exception):
	"""Thrown on a problem with the database."""
	pass

class IDatabase(Interface):
	"""
	Interface for accessing the server database.
	__init__() should set up initial database structure if necessary.
	All methods, including __init__() may throw a DatabaseException upon encountering problems.
	"""

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
		"""Return a list of User objects which are members of the given grid name."""
		pass

	def close(self):
		"""Commits all database changes and releases all resources, if applicable."""
		pass

class SQLiteDatabase(object):
	implements(IDatabase)

	def __init__(self, databaseFilename):
		try:
			self.connection = sqlite3.connect(databaseFilename)
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

		cursor.execute('CREATE TABLE IF NOT EXISTS regions(' +
		               'name VARCHAR(64) PRIMARY KEY NOT NULL,' +
		               'grid VARCHAR(64) NOT NULL,' +
		               'FOREIGN KEY(grid) REFERENCES grids(name)' +
		               ')')

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
		cursor.execute('CREATE TABLE IF NOT EXISTS regionHosts(' +
		               'regionName VARCHAR(64) NOT NULL,' +
		               'user CHAR(36) NOT NULL,' +
		               'regionHost BOOLEAN NOT NULL,' +
		               'FOREIGN KEY(regionName) REFERENCES regions(name),' +
		               'FOREIGN KEY(user) REFERENCES users(UUID)' +
		               ')')

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

		users = []
		for record in cursor.fetchall():
			user = User(record[0])
			user.firstName = record[1]
			user.lastName = record[2]
			user.moderator = record[3]
			user.gridHost = record[4]
			users.append(user)
		return users

	def close(self):
		if self.connection:
			self.connection.commit()
			self.connection.close()

if __name__ == "__main__":
	db = IDatabase(SQLiteDatabase('gridtogoserver.db'))

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

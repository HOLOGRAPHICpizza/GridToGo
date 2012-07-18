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

	def getGrid(self, gridName):
		"""Pull a full grid object from the database."""
		pass

	def storeGrid(self, grid):
		"""Create or update the record for the given Grid object."""
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
		cursor.execute('CREATE TABLE IF NOT EXISTS regions(' +
		               'name VARCHAR(64) PRIMARY KEY NOT NULL,' +
		               'firstName VARCHAR(64) NOT NULL,' +
		               'lastName VARCHAR(64) NOT NULL,' +
		               'hashedPassword VARCHAR(64) NOT NULL,' +
		               'email VARCHAR(64) NOT NULL' +
		               ')')
		cursor.execute('CREATE TABLE IF NOT EXISTS gridUsers(' +
		               'gridName VARCHAR(64) NOT NULL,' +
		               'user CHAR(36) NOT NULL,' +
		               'FOREIGN KEY(user) REFRENCES users(UUID),' +
		               'moderator BOOLEAN NOT NULL,' +
		               'gridHost BOOLEAN NOT NULL' +
		               ')')
		cursor.execute('CREATE TABLE IF NOT EXISTS gridRegions' +
		               'gridName VARCHAR(64) NOT NULL,' +
		               'user CHAR(36) NOT NULL,' +
		               'FOREIGN KEY(user) REFRENCES users(UUID),' +
		               'moderator BOOLEAN NOT NULL,' +
		               'gridHost BOOLEAN NOT NULL' +
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

	def getGrid(self, gridName):
		cursor = self.connection.cursor()
		cursor.execute('SELECT * FROM gridData WHERE gridName=?')

	def storeGrid(self, grid):
		pass

	def close(self):
		if self.connection:
			self.connection.commit()
			self.connection.close()

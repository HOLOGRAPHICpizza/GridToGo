from zope.interface import implements, Interface
import uuid
import hashlib
import sqlite3

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

	def getUserAccountByName(self, firstName, lastName):
		cursor = self.connection.cursor()
		cursor.execute('SELECT * FROM users WHERE firstName=? AND lastName=?', (firstName, lastName))
		row = cursor.fetchone()
		if row is None:
			return None
		return UserAccount(uuid.UUID(row[0]), row[1], row[2], row[3], row[4])

	def storeUserAccount(self, userAccount):
		cursor = self.connection.cursor()
		cursor.execute('INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?)',
			(str(userAccount.UUID),
			userAccount.firstName,
			userAccount.lastName,
			userAccount.hashedPassword,
			userAccount.email))
		self.connection.commit()

	def close(self):
		if self.connection:
			self.connection.commit()
			self.connection.close()

class DummyDatabase(object):
	implements(IDatabase)

	def __init__(self):
		UUID = uuid.UUID('cde17991-3122-464a-8dc0-65cad9b9dd67')
		hashedPassword = hashlib.sha224('testpass').hexdigest()
		userAccount = UserAccount(UUID, 'Michael', 'Craft', hashedPassword, True, False)
		# Maps full names to UserAccount objects
		self.users = {userAccount.firstName+' '+userAccount.lastName: userAccount}

	def getUserAccountByName(self, firstName, lastName):
		return self.users.get(firstName+' '+lastName)

	def storeUserAccount(self, userAccount):
		raise DatabaseException("Method not implemented.")

	def close(self):
		del self.users

# Main for testing
if __name__ == "__main__":
	UUID = uuid.UUID('cde17991-3122-464a-8dc0-65cad9b9dd67')
	hashedPassword = hashlib.sha224('testpass').hexdigest()
	userAccount = UserAccount(UUID, 'Michael', 'Craft', hashedPassword, True, False)

	db = IDatabase(SQLiteDatabase('gridtogoserver.db'))
	db.storeUserAccount(userAccount)
	userAccount2 = db.getUserAccountByName('Michael', 'Craft')
	pass

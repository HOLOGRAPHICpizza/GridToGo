from zope.interface import implements, Interface
import uuid
import hashlib

class UserAccount(object):
	def __init__(self, UUID, firstName, lastName, hashedPassword, online, natStatus):
		self.UUID = UUID
		self.firstName = firstName
		self.lastName = lastName
		self.hashedPassword = hashedPassword
		self.online = online
		self.natStatus = natStatus

class IDatabase(Interface):
	"""Interface for accessing the server database."""

	def getUserAccountByName(self, firstName, lastName):
		"""Returns None if no user found."""
		pass

class SQLiteDatabase(object):
	#TODO: Implement SQLite
	implements(IDatabase)

	def getUserAccountByName(self, firstName, lastName):
		return "Not implemented."

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

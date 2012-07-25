import uuid
from gridtogo.shared.networkobjects import *
from gi.repository import Gtk, Gdk
import os
from twisted.python import log

PREFIL_LOGIN_SAMPLE_DATA = True

def showModalDialog(parent, messageType, message):
	dialog = Gtk.MessageDialog(parent,
		Gtk.DialogFlags.MODAL,
		messageType,
		Gtk.ButtonsType.OK,
		message)
	dialog.run()
	dialog.destroy()

def loadImage(imageName, clientObject):
	return Gtk.Image.new_from_file(
		os.path.join(
			clientObject.projectRoot, "gridtogo", 'client', 'ui', imageName
		)
	)

class UserList(Gtk.VBox):
	"""This container will hold the visual list of users in the grid."""

	def __init__(self, clientObject):
		Gtk.VBox.__init__(self)

		# Images
		self.statusGrey = loadImage('status-grey.png', clientObject)
		self.statusYellow = loadImage('status-yellow.png', clientObject)
		self.statusGreen = loadImage('status-green.png', clientObject)
		self.gridHostActive = loadImage('gridhost-active.png', clientObject)
		self.gridHostInactive = loadImage('gridhost-inactive.png', clientObject)

		# Dictionary mapping UUIDs to HBoxes
		self.rows = {}

	def _getDefaultUser(self):
		defaultUser = User(None)
		defaultUser.firstName = '?'
		defaultUser.lastName = '?'
		defaultUser.online = False
		defaultUser.NATStatus = False
		defaultUser.gridHost = False
		return defaultUser

	def updateUser(self, user):
		"""Pass in a User object to add or update its entry."""
		row = Gtk.HBox()

		# Destroy the existing row, get user object
		oldRow = self.rows.get(user.UUID)
		newUser = self._getDefaultUser()
		if oldRow:
			newUser = oldRow.user
			oldRow.destroy()
		newUser.applyDelta(user)
		row.user = newUser

		#TODO: Set tooltips for things, or our users will be confuzzeled

		# Build the widgets
		status = self.statusGrey
		if newUser.online:
			status = self.statusYellow
			if newUser.NATStatus:
				status = self.statusGreen

		nameStr = newUser.firstName+' '+newUser.lastName
		if newUser.moderator:
			nameStr = "<b>%s</b>" % nameStr
		name = Gtk.Label(nameStr, use_markup=True)

		gridHost = self.gridHostInactive
		if newUser.gridHost:
			gridHost = self.gridHostActive

		# Pack the widgets
		row.pack_start(status, False, False, 0)
		row.pack_start(name, True, False, 0)
		row.pack_start(gridHost, False, False, 0)

		# Map the UUID to the row
		self.rows[newUser.UUID] = row

		# Pack the row
		self.pack_start(row, False, False, 0)
		row.show_all()

class SpinnerPopup(Gtk.Window):
	def __init__(self, parent, message):
		#TODO: Get some kind of padding on the outer edge of the window.
		Gtk.Window.__init__(
			self,
			type = Gtk.WindowType.POPUP,
			window_position = Gtk.WindowPosition.CENTER_ON_PARENT)

		self.set_transient_for(parent)

		self.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(255, 255, 255, 255))

		box = Gtk.VBox()
		self.add(box)

		spinner = Gtk.Spinner(width_request=75, height_request=75)
		#TODO: Override the spinner foreground color to black. Spinner needs special treatment.
		spinner.start()
		box.pack_start(spinner, False, False, 0)

		label = Gtk.Label(message)
		label.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(0, 0, 0, 255))
		box.pack_start(label, False, False, 0)

class WindowFactory(object):
	def __init__(self, clientObject):
		self.clientObject = clientObject

	def buildWindow(self, windowName, handlerClass):
		builder = Gtk.Builder()
		global PROJECT_ROOT_DIRECTORY
		builder.add_from_file(os.path.join(self.clientObject.projectRoot, "gridtogo", 'client', 'ui', windowName + '.glade'))
		handler = handlerClass(builder, self.clientObject, self, builder.get_object(windowName))
		builder.connect_signals(handler)
		return handler

class WindowHandler(object):
	def __init__(self, builder, clientObject, factory, window):
		self.builder = builder
		self.clientObject = clientObject
		self.factory = factory
		self.window = window

class LoginWindowHandler(WindowHandler):
	def __init__(self, builder, clientObject, factory, window):
		super(LoginWindowHandler, self).__init__(builder, clientObject, factory, window)
		self.firstNameEntry = builder.get_object("firstName")
		self.lastNameEntry = builder.get_object("lastName")
		self.passwordEntry = builder.get_object("password")
		self.gridEntry = builder.get_object("grid")

		if PREFIL_LOGIN_SAMPLE_DATA:
			self.firstNameEntry.set_text("test")
			self.lastNameEntry.set_text("user")
			self.passwordEntry.set_text("testpass")
			self.gridEntry.set_text("testgrid")

	def LANModeClicked(self, *args):
		log.msg("LAN Mode")

	def createUserClicked(self, *args):
		self.clientObject.createUserWindowHandler = self.factory.buildWindow("createUserWindow", CreateUserWindowHandler)
		self.clientObject.createUserWindowHandler.window.show_all()

	def loginClicked(self, *args):
		# register our stuff to be called then attempt connection
		self.clientObject.callOnConnected.append(self.onConnectionEstablished)
		#TODO: Read host:port from "Coordination Server" box
		self.clientObject.attemptConnection(self.window, 'localhost', 8017, 5)

	def onConnectionEstablished(self, protocol):
		firname = self.firstNameEntry.get_text()
		lasname = self.lastNameEntry.get_text()
		passwd = self.passwordEntry.get_text()
		grid = self.gridEntry.get_text()
		request = LoginRequest(firname, lasname, passwd, grid)
		self.clientObject.protocol.writeRequest(request)

		# de-register this method
		self.clientObject.callOnConnected.remove(self.onConnectionEstablished)

	def forgotPasswordClicked(self, *args):
		log.msg("forgot password")

	def quitClicked(self, *args):
		# Make sure we don't shut down the whole application if we are logged in
		if not self.clientObject.mainWindowHandler:
			self.clientObject.stop()

class CreateUserWindowHandler(WindowHandler):
	def __init__(self, builder, clientObject, factory, window):
		super(CreateUserWindowHandler, self).__init__(builder, clientObject, factory, window)
		self.emailEntry = builder.get_object("entryEMail")
		self.firstNameEntry = builder.get_object("entryFirstName")
		self.lastNameEntry = builder.get_object("entryLastName")
		self.passwordEntry = builder.get_object("entryPassword")
		self.passwordRetypeEntry = builder.get_object("entryRetypePassword")

	def destroy(self):
		self.window.destroy()

	def createUserClicked(self, *args):
		email = self.emailEntry.get_text()
		firstName = self.firstNameEntry.get_text()
		lastName = self.firstNameEntry.get_text()
		passwordEntry = self.passwordEntry.get_text()
		passwordRetypeEntry = self.passwordRetypeEntry.get_text()

		if passwordEntry != passwordRetypeEntry:
			showModalDialog(self.window, Gtk.MessageType.ERROR, "Passwords do not match.")
			return

		# Register our method and attempt connection
		self.clientObject.callOnConnected.append(self.connectionEstablished)
		#TODO: Read host:port from "Coordination Server" box
		self.clientObject.attemptConnection(self.window, 'localhost', 8017, 5)
		
	def onCreateUserSuccess(self):
		showModalDialog(self.window, Gtk.MessageType.INFO, CreateUserSuccess().message)
		self.destroy()

	def connectionEstablished(self, protocol):
		email = self.emailEntry.get_text()
		firstName = self.firstNameEntry.get_text()
		lastName = self.lastNameEntry.get_text()
		passwordEntry = self.passwordEntry.get_text()

		request = CreateUserRequest(firstName, lastName, passwordEntry, email)
		self.clientObject.protocol.writeRequest(request)

		# de-register this method
		self.clientObject.callOnConnected.remove(self.connectionEstablished)

	def cancelClicked(self, *args):
		self.destroy()

class MainWindowHandler(WindowHandler):

	def __init__(self, builder, clientObject, factory, window):
		super(MainWindowHandler, self).__init__(builder, clientObject, factory, window)
		
		vbox = builder.get_object("vbox")
		list = UserList(clientObject)
		list.updateUser(None)
		vbox.pack_start(list, False, False, 0)

	def onbtnNewRegionClicked(self, *args):
		self.clientObject.createRegionWindowHandler = \
		self.factory.buildWindow("createRegionWindow", createRegionWindowHandler)
		print self.clientObject.createRegionWindowHandler
		self.clientObject.createRegionWindowHandler.window.show_all()

	def PopulateTable(self):

		#take the data recieved and sort it accordingly
		
		#if self.Vbox:
		#	self.vbox.destroy()
		#self.Vbox = gtk.VBox(False)
		
		#hbox = gtk.Hbox(False)

		pass

	def destroy(self):
		self.destroy()


		# Create UserList
		vbox = builder.get_object("vbox")
		self.userList = UserList(clientObject)
		vbox.pack_start(self.userList, False, False, 0)
		self.userList.show_all()

	def onbtnNewRegionClicked(self, *args):
		self.clientObject.windowCreateRegionHandler = self.factory.buildWindow("createRegionWindow", windowCreateRegionHandler)
		self.clientObject.windowCreateRegionHandler.window.show_all()

	def destroy(self, arg):
		self.window.destroy()
		self.clientObject.stop()

class createRegionWindowHandler(WindowHandler):
	def __init__(self, builder, clientObject, factory, window):
		super(createRegionWindowHandler, self).__init__(builder, clientObject, factory, window)
		
		self.regionName = builder.get_object("entRegionName")
		self.location = builder.get_object("entLocation")
		self.externalHostname = builder.get_object("entExtHostname")

	def onbtnCreateRegionClicked(self, *args):
		region = self.regionName.get_text()
		coordinates = self.location.get_text()
		hostname = self.externalHostname.get_text()

		
	def onbtnCancelClicked(self, *args):
		self.window.destroy()

	def destroy(self):
		self.window.destroy()

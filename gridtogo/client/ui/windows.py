#Windows.py
#Holds the handlers for all of the forms, as well as their methods
import uuid
from gridtogo.client.opensim.distribution import Distribution
import gridtogo.client.process as process
from gridtogo.shared.networkobjects import *
from gridtogo.client.ui.dialog import *
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
import os
from twisted.python import log
from twisted.internet import protocol, reactor
from twisted.internet.defer import Deferred

PREFIL_LOGIN_SAMPLE_DATA = True

def loadPixbuf(imageName, clientObject):
	return GdkPixbuf.Pixbuf.new_from_file(
		os.path.join(
			clientObject.projectRoot, "gridtogo", 'client', 'ui', imageName
		)
	)

class UserList(Gtk.ListStore):
	"""This container will hold the visual list of users in the grid."""

	def __init__(self, clientObject):
		Gtk.ListStore.__init__(self, GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf, str, GdkPixbuf.Pixbuf, int, int, int)
		# Images for the main window
		self.clientObject = clientObject
		self.statusGrey = loadPixbuf('status-grey.png', clientObject)
		self.statusYellow = loadPixbuf('status-yellow.png', clientObject)
		self.statusGreen = loadPixbuf('status-green.png', clientObject)
		self.gridHostActive = loadPixbuf('gridhost-active.png', clientObject)
		self.gridHostInactive = loadPixbuf('gridhost-inactive.png', clientObject)
		self.moderator = loadPixbuf('shield.png', clientObject)
		self.blank = loadPixbuf('blank24.png', clientObject)

		# Dictionary mapping UUIDs to Iterators
		self.iterators = {}

		# Do initial population
		for uuid in clientObject.users:
			self.updateUser(clientObject.users[uuid])

	def updateUser(self, newUser):
		"""Pass in a User object to add or update its entry."""
		# Destroy the existing row, get user object
		iterator = self.iterators.get(newUser.UUID)
		if iterator is None:
			iterator = self.append()

		#TODO: Set tooltips for things, or our users will be confused

		# Build the widgets
		status = None
		statusI = None
		if newUser.online and not newUser.NATStatus:
			status = self.statusYellow
			statusI = 2
		elif newUser.online and newUser.NATStatus:
			status = self.statusGreen
			statusI = 1
		else:
			status = self.statusGrey
			statusI = 3

		# Make name bold if this is the local user
		sub = "%s %s"
		if newUser.UUID == self.clientObject.localUUID:
			sub = "<b>%s %s</b>"
		name = sub % (newUser.firstName, newUser.lastName)

		gridHost = None
		gridHostI = None
		if newUser.gridHost and not newUser.gridHostActive:
			gridHost = self.gridHostInactive
			gridHostI = 2
		elif newUser.gridHost and newUser.gridHostActive:
			gridHost = self.gridHostActive
			gridHostI = 1
		else:
			gridHost = self.blank
			gridHostI = 3

		moderatorI = None
		if newUser.moderator:
			moderatorIcon = self.moderator
			moderatorI = 1
		else:
			moderatorIcon = self.blank
			moderatorI = 2
	
		self.set_value(iterator, 0, status)
		self.set_value(iterator, 1, moderatorIcon)
		self.set_value(iterator, 2, name)
		self.set_value(iterator, 3, gridHost)

		# Not Rendered, but used for sorting
		self.set_value(iterator, 4, statusI)
		self.set_value(iterator, 5, moderatorI)
		self.set_value(iterator, 6, gridHostI)

		# Map the UUID to the iterator
		self.iterators[newUser.UUID] = iterator

class RegionList(Gtk.ListStore):
	"""This container will hold the visual list of users in the grid."""

	def __init__(self, clientObject):
		Gtk.ListStore.__init__(self, str, str, str)

		# Dictionary mapping names to GtkTreeIter
		self.iterators = {}

		# Do initial population
		for k in clientObject.regions:
			self.updateRegion(clientObject.regions[k])

	def updateRegion(self, region):
		"""Pass in a User object to add or update its entry."""
		# Destroy the existing row, get region object
		iterator = self.iterators.get(region.regionName)
		if iterator is None:
			# Add a new location
			iterator = self.append()

		self.set_value(iterator, 0, region.regionName)
		self.set_value(iterator, 1, region.location)
		if region.currentHost is None:
			self.set_value(iterator, 2, "None")
		else:
			self.set_value(iterator, 2, self.clientObject.users[region.currentHost])

		# Map the name to the row
		self.iterators[region.regionName] = iterator

class SpinnerPopup(Gtk.Window):
	"""
	Example of call, does not block, parent can be None:
		spinner = SpinnerPopup(spinnerParent, 'Connecting...')
		spinner.show_all()
		# do stuff
		spinner.destroy()
	"""
	def __init__(self, parent, message):
		#TODO: Get some kind of padding on the outer edge of the window.
		Gtk.Window.__init__(
			self,
			type = Gtk.WindowType.POPUP,
			window_position = Gtk.WindowPosition.CENTER_ON_PARENT)

		self.set_transient_for(parent)

		self.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(255, 255, 255, 255))

		self.box = Gtk.VBox()
		self.add(self.box)

		spinner = Gtk.Spinner(width_request=75, height_request=75)
		#TODO: Override the spinner foreground color to black. Spinner needs special treatment.
		spinner.start()
		self.box.pack_start(spinner, False, False, 0)

		self.label = None
		self.setMessage(message)

	def setMessage(self, message):
		if self.label:
			self.label.destroy()
		self.label = Gtk.Label(message)
		self.label.override_color(Gtk.StateType.NORMAL, Gdk.RGBA(0, 0, 0, 255))
		self.box.pack_end(self.label, False, False, 0)
		self.label.show()

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
		self.userCreateActive = False

		if PREFIL_LOGIN_SAMPLE_DATA:
			self.firstNameEntry.set_text("test")
			self.lastNameEntry.set_text("user")
			self.passwordEntry.set_text("testpass")
			self.gridEntry.set_text("testgrid")

	def LANModeClicked(self, *args):
		log.msg("LAN Mode")

	def createUserClicked(self, *args):
		
		if self.userCreateActive == False:
			self.clientObject.createUserWindowHandler = self.factory.buildWindow("createUserWindow", CreateUserWindowHandler)
			self.clientObject.createUserWindowHandler.window.show_all()
			self.userCreateActive = True
		elif self.userCreateActive == True:
			showModalDialog(self.window, Gtk.MessageType.ERROR, "The form is already up!")

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
		#The login window shouldn't be up when the main is
		if not self.clientObject.mainWindowHandler:
			self.clientObject.dieing = True
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
		if self.window:
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
		LoginWindowHandler.userCreateActive = False
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
		LoginWindowHandler.userCreateActive = False
		self.destroy()

class MainWindowHandler(WindowHandler):

	def __init__(self, builder, clientObject, factory, window):
		super(MainWindowHandler, self).__init__(builder, clientObject, factory, window)

		# Status bar
		# Do not directly use this, call setStatus
		self._statusbar = builder.get_object('statusbar')

		# Create UserList
		vbox = builder.get_object("usersBox")
		self.userList = UserList(clientObject)
		self.userView = Gtk.TreeView(model=self.userList)
		self.userView.get_selection().set_mode(Gtk.SelectionMode.NONE)

		statusrenderer = Gtk.CellRendererPixbuf()
		statuscol = Gtk.TreeViewColumn()
		statuscol.pack_start(statusrenderer, True)
		statuscol.add_attribute(statusrenderer, "pixbuf", 0)
		statuscol.set_sort_column_id(4)
		statuscol.set_title("Status")
		statuscol.set_alignment(0.5)

		moderatorrenderer = Gtk.CellRendererPixbuf()
		moderatorcol = Gtk.TreeViewColumn()
		moderatorcol.pack_start(moderatorrenderer, True)
		moderatorcol.add_attribute(moderatorrenderer, "pixbuf", 1)
		moderatorcol.set_sort_column_id(5)
		moderatorcol.set_title("Moderator")
		moderatorcol.set_alignment(0.5)

		namerenderer = Gtk.CellRendererText()
		namecol = Gtk.TreeViewColumn()
		namecol.pack_start(namerenderer, True)
		namecol.add_attribute(namerenderer, "markup", 2)
		namecol.set_sort_column_id(2)
		namecol.set_title("Name")

		gridhostrenderer = Gtk.CellRendererPixbuf()
		gridhostcol = Gtk.TreeViewColumn()
		gridhostcol.pack_start(gridhostrenderer, True)
		gridhostcol.add_attribute(gridhostrenderer, "pixbuf", 3)
		gridhostcol.set_sort_column_id(6)
		gridhostcol.set_title("Grid Host")
		gridhostcol.set_alignment(0.5)

		self.userView.append_column(statuscol)
		self.userView.append_column(moderatorcol)
		self.userView.append_column(namecol)
		self.userView.append_column(gridhostcol)

		vbox.pack_start(self.userView, False, False, 0)
		self.userView.show_all()
		
		# Create RegionList
		regionbox = builder.get_object("regionsBox")
		self.regionList = RegionList(clientObject)
		self.regionView = Gtk.TreeView(model=self.regionList)

		namerenderer = Gtk.CellRendererText()
		namecol = Gtk.TreeViewColumn()
		namecol.pack_start(namerenderer, True)
		namecol.add_attribute(namerenderer, "text", 0)
		namecol.set_sort_column_id(0)
		namecol.set_title("Name")

		locationrenderer = Gtk.CellRendererText()
		locationcol = Gtk.TreeViewColumn()
		locationcol.pack_start(locationrenderer, True)
		locationcol.add_attribute(locationrenderer, "text", 1)
		locationcol.set_sort_column_id(1)
		locationcol.set_title("Location")

		hostrenderer = Gtk.CellRendererText()
		hostcol = Gtk.TreeViewColumn()
		hostcol.pack_start(hostrenderer, True)
		hostcol.add_attribute(hostrenderer, "text", 2)
		#hostcol.set_sort_column_id(2)
		hostcol.set_title("Host")

		self.regionView.append_column(namecol)
		self.regionView.append_column(locationcol)
		self.regionView.append_column(hostcol)

		regionbox.pack_start(self.regionView, False, False, 0)
		self.regionView.show_all()

	def setStatus(self, message):
		"""Set the contents of the status bar."""

		# Get a stupid GTK context id
		if not hasattr(self, '_statusContext'):
			self._statusContext = self._statusbar.get_context_id('GridToGo Status Bar')

		self._statusbar.pop(self._statusContext)
		self._statusbar.push(self._statusContext, message)

	def updateUser(self, user):
		# Update the title bar
		if user.UUID == self.clientObject.localUUID:
			localUser = self.clientObject.users[user.UUID]
			self.window.set_title(
				"GridToGo - %s %s"
				% (localUser.firstName, localUser.lastName))

		self.userList.updateUser(user)

	def destroy(self, *args):
		self.window.destroy()
		self.clientObject.dieing = True
		self.clientObject.stop()
		
	def onbtnNewRegionClicked(self, *args):
		#TODO: Prevent users from opening the Create Region window multiple times. not a problem, but more of a common sense thing.
		self.clientObject.CreateRegionWindowHandler = \
		self.factory.buildWindow("createRegionWindow", CreateRegionWindowHandler)
		print self.clientObject.CreateRegionWindowHandler
		self.clientObject.CreateRegionWindowHandler.window.show_all()
	
	def onHostRegion(self, *args):
		(model, iterator) = self.regionView.get_selection().get_selected()
		regionName = model[iterator][0]
		log.msg("Trying to host region " + regionName)
		log.msg("Region Hosts: " + str(self.clientObject.regions[regionName].hosts))
		region = self.clientObject.regions[regionName]
		user = self.clientObject.getLocalUser()
		if user.UUID in region.hosts:
			log.msg("Hosting region " + regionName)
			delta = DeltaRegion(regionName)
			delta.currentHost = user.UUID
			self.clientObject.protocol.writeRequest(delta)

			#TODO: Don't hardcode gridname and localhost
			distribution = Distribution(self.clientObject.projectRoot, parent=self.window)

			def hostRegion(dist):
				log.msg("Configuring region for hosting")

				#TODO: Don't hardcode port
				port = 9000

				# Do region-agnostic configuration
				dist.configure("GridName", "localhost")
				# Do region-specific configuration
				dist.configureRegion(region.regionName, region.location, region.externalhost, port)

				# We use the convention: consolePort = port + 10000
				protocol_ = process.spawnRegionProcess(
					dist.opensimdir,
					region.regionName,
					port + 10000,
					callOnOutput=self.clientObject.processSimOutput)

				self.clientObject.processes[region.regionName] = protocol_
				
			d = Deferred()
			d.addCallback(hostRegion)
			distribution.load(d)

		else:
			showModalDialog(
				self.window,
				Gtk.MessageType.ERROR,
				"Not allowed to host region.")

	def becomeGridHost(self, *args):
		if self.clientObject.getLocalUser().gridHost:
			for uuid in self.clientObject.users:
				if self.clientObject.users[uuid].gridHostActive:
					#TODO: Allow moderators to take gridhost from others.
					showModalDialog(
						self.window,
						Gtk.MessageType.ERROR,
						'The grid is already being hosted.'
					)
					return

			delta = DeltaUser(self.clientObject.getLocalUser().UUID)
			delta.gridHostActive = True

			# The delta gets applied when the server echos it back
			#self.clientObject.updateUser(delta)
			self.clientObject.protocol.writeRequest(delta)

			#TODO: Show error dialogs on failures

			self.setStatus('Loading OpenSim distribution...')

			distribution = Distribution(self.clientObject.projectRoot, parent=self.window)
			d = Deferred()
			d.addCallback(self.startRobust)
			distribution.load(d)
			#TODO: Don't hardcode this

		else:
			showModalDialog(
				self.window,
				Gtk.MessageType.ERROR,
				'You do not have permission to become the grid host.'
			)

	def startRobust(self, distribution):
		self.setStatus('Configuring ROBUST...')
		distribution.configureRobust(self.clientObject.localGrid, "localhost")

		self.setStatus('Grid Server (ROBUST) is starting...')
		protocol_ = process.spawnRobustProcess(
			distribution.opensimdir,
			self.clientObject.robustEnded,
			self.clientObject.processRobustOutput)
		#console = ConsoleWindow(protocol)
		#console.show_all()

		self.clientObject.processes['ROBUST'] = protocol_


	def manageServices(self, *args):
		"""Spawn a window to kill services or connect to their consoles."""
		RunningServicesWindow(self.clientObject).show_all()

class RunningServicesWindow(Gtk.Window):
	"""
	A one-time-use window to kill services or connect to their consoles.
	Destroys itself when a console is spawned.
	"""

	#TODO: Make this a modal dialog with standardized dialog button layout

	def __init__(self, clientObject):
		"""processes is a dict mapping process names to process protocols."""
		Gtk.Window.__init__(self)

		self.clientObject = clientObject

		vbox = Gtk.VBox()
		self.add(vbox)

		listStore = Gtk.ListStore(str)

		self.treeView = Gtk.TreeView(model=listStore)
		vbox.pack_start(self.treeView, False, False, 0)

		namerenderer = Gtk.CellRendererText()
		namecol = Gtk.TreeViewColumn()
		namecol.pack_start(namerenderer, True)
		namecol.add_attribute(namerenderer, "text", 0)
		namecol.set_sort_column_id(0)
		namecol.set_title("Process Name")
		self.treeView.append_column(namecol)

		for processName in self.clientObject.processes:
			iterator = listStore.append()
			listStore.set_value(iterator, 0, processName)

		# Buttons
		hbox = Gtk.HBox()
		vbox.pack_end(hbox, False, False, 0)

		viewConsole = Gtk.Button('View Console')
		viewConsole.connect('clicked', self.viewConsole)
		hbox.pack_start(viewConsole, False, False, 0)

		killProcess = Gtk.Button('Kill Process')
		killProcess.connect('clicked', self.killProcess)
		hbox.pack_start(killProcess, False, False, 0)

		#TODO: Use stock cancel button
		cancel = Gtk.Button('Cancel')
		cancel.connect('clicked', self.cancel)
		hbox.pack_end(cancel, False, False, 0)

	def getSelectedProcess(self):
		(model, iterator) = self.treeView.get_selection().get_selected()
		processName = model[iterator][0]
		return self.clientObject.processes[processName]

	def viewConsole(self, *args):
		process = self.getSelectedProcess()

		args = [os.path.join(process.opensimdir, 'bin', 'OpenSim.ConsoleClient.exe'),
		        '-host', 'localhost',
		        '-port', str(process.consolePort),
		        '-user', 'gridtogo',
		        '-pass', 'gridtogopass',
		        '-prompt', process.name]

		dump = ''
		dumpList = ['xterm', '-fg', 'white', '-bg', 'black', '-sl', '3000', '-e', 'mono'] + args
		for item in dumpList:
			dump += item + ' '
		print dump

		if os.name == 'nt':
			raise NotImplementedError('Running on Windows is not yet supported.')
		else:
			reactor.spawnProcess(
				protocol.ProcessProtocol(),
				'xterm',
				['xterm', '-fg', 'white', '-bg', 'black', '-sl', '3000', '-e', 'mono'] + args,
				os.environ,
				os.path.join(process.opensimdir, 'bin'))

		self.destroy()

	def killProcess(self, *args):
		self.getSelectedProcess().transport.signalProcess('KILL')
		self.destroy()

	def cancel(self, *args):
		self.destroy()

class CreateRegionWindowHandler(WindowHandler):
	def __init__(self, builder, clientObject, factory, window):
		super(CreateRegionWindowHandler, self).__init__(builder, clientObject, factory, window)
		self.regionName = builder.get_object("entRegionName")
		self.location = builder.get_object("entLocation")
		self.externalHostname = builder.get_object("entExtHostname")

	def onbtnCreateRegionClicked(self, *args):
		region = self.regionName.get_text()
		coordinates = self.location.get_text()
		hostname = self.externalHostname.get_text()

		#TODO: Don't hardcode gridname and localhost
		distribution = Distribution(self.clientObject.projectRoot)
		distribution.configure("GridName", "localhost")

		# TODO Don't hardcode port
		distribution.configureRegion(region, coordinates, hostname, 9000)

		# Actually store the region in the database
		gridName = self.clientObject.localGrid
		uuid = self.clientObject.localUUID
		request = CreateRegionRequest(uuid, gridName, region, coordinates, hostname)
		self.clientObject.protocol.writeRequest(request)
		self.destroy()
		
	def btnCancelClicked(self, *args):
		self.destroy()

	def destroy(self):
		if self.window:
			self.window.destroy()


class ConsoleWindow(Gtk.Window):
	def __init__(self, protocol):
		Gtk.Window.__init__(self)

		self.protocol = protocol
		self.protocol.window = self
		
		self.vbox = Gtk.VBox()
		self.scroll = Gtk.ScrolledWindow()
		self.outputArea = Gtk.TextView()
		self.outputArea.set_sensitive(False)
		self.scroll.add(self.outputArea)
		
		self.vbox.pack_start(self.scroll, True, True, 0)

		self.entryfield = Gtk.Entry()
		self.entryfield.connect('activate', self.enter_pressed)
		self.vbox.pack_start(self.entryfield, False, False, 0)

		self.add(self.vbox)

		self.outputArea.get_buffer().set_text(self.protocol.allData)
	
	def outReceived(self, data):
		self.outputArea.get_buffer().set_text(self.protocol.allData)
	
	def enter_pressed(self, something):
		self.protocol.transport.write(self.entryfield.get_text() + "\n")
		self.entryfield.get_buffer().set_text("", 0)

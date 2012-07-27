# GridToGo
## An easy to use GUI for creating and managing ad-hoc OpenSim grids.

GridToGo aims to fill the currently empty niche of a simple, self-contained program to create and manage decentralized [OpenSim](http://opensimulator.org/) grids on end-user machines, such as laptops. Lets put OpenSim in the hands of anyone who wants to play with it by removing the traditional reliance on a big complicated grid server, and making as easy as joining a friend's game in any modern online video game.

GridToGo is written in Python 2 utilizing the GTK+ 3 GUI toolkit through the PyGObject bindings. This means it is technically completely cross-platform, but it is currently only tested on Linux. The current immature state of the GTK+ 3 bindings in Windows make it very difficult to install this program correctly.

GridToGo was created for [Summer At The Edge 2012](http://wbi-icc.com/centers-services/discovery-lab) under the direction of Dr. Rob Williams and is released under the MIT license.

External Dependencies:
- Python >= 2.7 && < 3.0 (May work on previous versions of Python 2.X, untested) with SQLite support
- Twisted >= 12.1.0 with GTK+ support
- PyGObject >= 3.0.0 with introspection support
- A database backend:
* SQLite (Tested only on SQLite3)
* MongoDB and PyMongo

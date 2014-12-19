# -*- coding: utf-8 -*-
# linstaller userhost module install - (C) 2011 Eugenio "g7" Paolantonio and the Semplice Team.
# All rights reserved. Work released under the GNU GPL license, version 3 or later.
#
# This is a module of linstaller, should not be executed as a standalone application.

import linstaller.frontends.cli as cli
import linstaller.core.main as m
import t9n.library
_ = t9n.library.translation_init("linstaller")

from linstaller.core.main import warn,info,verbose

class Frontend(cli.Frontend):
	def start(self):
		""" Start the frontend """

		# Get a progressbar
		progress = self.progressbar(_("Creating user:"), 3)
		progress.start()
		
		try:
			verbose("Creating user")
			# USER: set.
			self.moduleclass.install.user_set()
			progress.update(1)
			
			# USER: commit.
			self.moduleclass.install.user_commit()
			progress.update(2)
			
			verbose("Setting username")
			# HOSTNAME: commit
			self.moduleclass.install.host_commit()
			progress.update(3)
		finally:
			# Exit
			self.moduleclass.install.close()
		
		progress.finish()


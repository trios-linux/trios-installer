# -*- coding: utf-8 -*-
# linstaller end module frontend - (C) 2011 Eugenio "g7" Paolantonio and the Semplice Team.
# All rights reserved. Work released under the GNU GPL license, version 3 or later.
#
# This is a module of linstaller, should not be executed as a standalone application.

import os
import sys
import linstaller.frontends.cli as cli
import t9n.library
_ = t9n.library.translation_init("linstaller")

class Frontend(cli.Frontend):
	def start(self):
		""" Start the frontend """
		
		self.header(_("Enjoy"))
		
		print(_("Just finished the installation of %(distribution)s.") % {"distribution":self.moduleclass.main_settings["distro"]})
		print(_("Please reboot and remove the install media to get the installed system."))
		print

		try:
		  os.system("/usr/bin/copy-install-log.sh")
		except: 
		  pass
		
		if not self.settings["reboot"]:
			# We should continue?
			res = self.question(_("Do you want to reboot now?"), default=True)
			if res:
				# Reboot
				return "kthxbye"
			else:
				self.end()
		else:
			# Reboot.
			return "kthxbye"
			

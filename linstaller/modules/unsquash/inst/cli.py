# -*- coding: utf-8 -*-
# linstaller unsquash module install - (C) 2011 Eugenio "g7" Paolantonio and the Semplice Team.
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

		verbose("Calculating the number of the files to copy...")
		filenum = self.moduleclass.unsquash.get_files()
		
		# Get a progressbar
		progress = self.progressbar(_("Copying system to disk:"), filenum)
		
		verbose("Beginning copying system")
		# Launch unsquashfs
		unsquashfs = self.moduleclass.unsquash.begin()

		# Start progressbar
		progress.start()
		
		# Update progressbar
		unsquashfs.process.poll()
		
		output = [None]
		while unsquashfs.process.poll() == None:
			try:
				toappend = unsquashfs.process.stdout.readline()
				if output[-1] != toappend:
					output.append(toappend)
					
					num = len(output)
					
					# If num > filenum, the progressbar will crash.
					if not num > filenum:
						progress.update(num)
			except:
				# It may fail when resizing the terminal window.
				# This will cause unsync between the progressbar and the unsquashing process.
				# But it's better than let the installer crash ;-)
				pass
		progress.finish()
		
		if unsquashfs.process.returncode != 0:
			# Write the output into the log file
			for line in output:
				verbose(str(line))
			raise m.CmdError(_("An error occoured while uncompressing system to disk."))
		
		verbose("System copied successfully.")
		
		# Mount.
		verbose("Mounting /proc, /dev and /sys")
		
		self.moduleclass.unsquash.mount()

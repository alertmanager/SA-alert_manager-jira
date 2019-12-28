import os
import logging
from logging.config import fileConfig
import ConfigParser
import splunk.appserver.mrsparkle.lib.util as util

def setupLogger(logger='alert_manager-jira'):

	# logger
	fileName = 'alert_manager-jira.log'
	if logger != 'alert_manager-jira':
		fileName = 'alert_manager-jira_%s.log' % logger
		logger = 'alert_manager-jira_%s' % logger

	# Get loglevel from config file
	local = os.path.join(util.get_apps_dir(), "SA-alert_manager-jira", "local", "alert_manager-jira.conf")
	default = os.path.join(util.get_apps_dir(), "SA-alert_manager-jira", "default", "alert_manager-jira.conf")

	config = ConfigParser.ConfigParser()

	try:
		config.read(local)
		rootLevel = config.get('logging', 'rootLevel')
	except:
		config.read(default)
		rootLevel = config.get('logging', 'rootLevel')

	try:
		logLevel = config.get('logging', 'logger.%s' % logger)
	except:
		logLevel = rootLevel

	# Setup logger
	log = logging.getLogger(logger)
	lf = os.path.join(os.environ.get('SPLUNK_HOME'), "var", "log", "splunk", fileName)
	fh = logging.handlers.RotatingFileHandler(lf, maxBytes=25000000, backupCount=5)
	formatter = logging.Formatter('%(asctime)s %(levelname)-6s pid="%(process)s" logger="%(name)s" message="%(message)s" (%(filename)s:%(lineno)s)')
	fh.setFormatter(formatter)
	log.addHandler(fh)
	level = logging.getLevelName(logLevel)
	log.setLevel(level)

	return log

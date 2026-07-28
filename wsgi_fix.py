import sys
path = '/var/www/sprintwisp/sprint/'
if path not in sys.path:
    sys.path.append(path)

from app import app as application

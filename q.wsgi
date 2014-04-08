import os
basedir = '/var/www/apps/'

log_collection='task_log'
tomb_collection ='cybercom_queue_meta'

activate_this = basedir + 'q/virtpy/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import site
site.addsitedir(basedir + 'q')
import cherrypy
from cherrypy import wsgiserver
from q import q

    
application = cherrypy.Application(q.Root(log_collection=q.config.MONGO_LOG_COLLECTION,
    tomb_collection=q.config.MONGO_TOMBSTONE_COLLECTION), 
    script_name=None, config = None )# , 
    config={ '/': {'tools.xmlrpc.on': Fales  }} )

if __name__ == '__main__':
    wsgi_apps = [('/q', application)]
    server = wsgiserver.CherryPyWSGIServer(('localhost', 8080), wsgi_apps, server_name='localhost')
    try:
        server.start()
    except KeyboardInterrupt():
        server.stop()



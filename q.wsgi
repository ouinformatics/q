import os
if os.uname()[1] == 'fire.rccc.ou.edu':
    basedir = '/scratch/www/wsgi_sites/'
elif os.uname()[1][:2] == 'ip':
    #running on aws
    basedir = '/var/www_apps/'
else:
    basedir = '/var/www/apps/'

if os.uname()[1] == 'test.oklahomawatersurvey.org' or os.uname()[1] == 'data.oklahomawatersurvey.org':
    log_collection='ows_task_log'
    tomb_collection ='okwater'
else:
    log_collection='task_log'
    tomb_collection ='cybercom_queue_meta'

activate_this = basedir + 'q/virtpy/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import site
site.addsitedir(basedir + 'q')
import cherrypy
from cherrypy import wsgiserver
from q.q import Root

    
application = cherrypy.Application(Root(log_collection=log_collection,tomb_collection=tomb_collection), script_name=None, config = None )# , config={ '/': {'tools.xmlrpc.on': True }} )

if __name__ == '__main__':
    wsgi_apps = [('/q', application)]
    server = wsgiserver.CherryPyWSGIServer(('localhost', 8080), wsgi_apps, server_name='localhost')
    try:
        server.start()
    except KeyboardInterrupt():
        server.stop()



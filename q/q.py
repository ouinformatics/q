#from pymongo import Connection 
import cherrypy
from json_handler import handler
import simplejson as json
from celery.task.control import inspect
from celery.result import AsyncResult
from celery.execute import send_task
from pymongo import Connection
from datetime import datetime
import pickle


class jsonify( object ):
    """ JSONify a Python dictionary """  
    def __init__(self,f):
        self.f = f
 
    def __call__(self, *args, **kwargs ):
        results = self.f(*args, **kwargs)
        j = json.dumps( results )
        return j

def check_memcache(host="127.0.0.1", port=11211):
    """ Check if memcache is running on server """
    import socket
    s = socket.socket()
    try:
        s.connect((host,port))
        return True
    except:
        return False

if check_memcache():
    import memcache
else:
    memcache = None

def update_tasks(timeout=600, user="guest"):
    """ 
    Get list of registered tasks from celery, store in memcache for 
        `timeout` period if set (default to 600s) if available 
    """
    i = inspect()
    if memcache:
        mc = memcache.Client(['127.0.0.1:11211'])
        tasks = "REGISTERED_TASKS_%s" % user
        queues = "AVAILABLE_QUEUES_%s" % user
        REGISTERED_TASKS = mc.get(tasks)
        AVAILABLE_QUEUES = mc.get(queues)
        if not REGISTERED_TASKS:
            REGISTERED_TASKS = set()
            for item in i.registered().values():
                REGISTERED_TASKS.update(item)
            mc.set(tasks, REGISTERED_TASKS, timeout)
            REGISTERED_TASKS = mc.get(tasks)
        if not AVAILABLE_QUEUES:
            mc.set(queues, set([ item[0]["exchange"]["name"] for item in i.active_queues().values() ]), timeout)
            AVAILABLE_QUEUES = mc.get(queues)
    else:
        REGISTERED_TASKS = set()
        for item in i.registered().values():
            REGISTERED_TASKS.update(item)
        AVAILABLE_QUEUES = set([item[0]["exchange"]["name"] for item in i.active_queues().values() ])
    return (REGISTERED_TASKS, AVAILABLE_QUEUES)    

def list_tasks():
    """ Dump a list of registred tasks """ 
    REGISTERED_TASKS, AVAILABLE_QUEUES = update_tasks()
    REGISTERED_TASKS = [ task for task in list(REGISTERED_TASKS) if task[0:6] != "celery" ]
    AVAILABLE_QUEUES = list(AVAILABLE_QUEUES) 
    REGISTERED_TASKS.sort()
    AVAILABLE_QUEUES.sort()
    return { "available_tasks": REGISTERED_TASKS, "available_queues": AVAILABLE_QUEUES }

def reset_tasks(user):
    """ 
    Delete and reload memcached record of available tasks, useful for development
        when tasks are being frequently reloaded.
    """
    if memcache:
        mc = memcache.Client(['127.0.0.1:11211'])
        tasks = "REGISTERED_TASKS_%s" % user
        queues = "AVAILABLE_QUEUES_%s" % user
        mc.delete(tasks)
        mc.delete(queues)
    return list_tasks()


def check_user(login):
    if login:
        user = login
    else:
        user = "guest"    
    return user

    
def check_auth(user_id):
    pass 
class Root():
    def __init__(self,mongoHost='localhost',port=27017,database='cybercom_queue',log_collection='task_log',tomb_collection='cybercom_queue_meta'):
        self.db = Connection(mongoHost,port)#[database]
        self.database = database
        self.collection = log_collection #'ows_task_log'
        self.tomb_collection= tomb_collection #'cybercom_queue_meta'#'okwater'#'cybercom_queue_meta'
    def index(self):
        """ Index method for queue run """ 
        pass
    
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def run(self,**GETargs): 
        """ 
        Run a task in the task queue:
        curl --data-ascii '{ "function": "function.name", 
            "queue": "queuename", 
            "args": ["list","of","arguments"],
            "kwargs": {"object": "of", "keyword": "arguments"}
        }' http://somehostname.com/q/run/ -H Content-Type:application/json

        Optional GET Arguments:
        - `callback` - JSONP Callback
        
        """
        # Parse arguments from JSON
        args = cherrypy.request.json
        tasks = list_tasks()
        funcs = tasks['available_tasks']
        queues = tasks['available_queues']

        # Make sure a function name was specified
        if args.has_key('function'):
            function = args['function']
            if function not in funcs:
                raise cherrypy.HTTPError(400, "function name not found")
        else:
            raise cherrypy.HTTPError(400, "JSON missing `function` key")

        # Make sure queue name was specified        
        if args.has_key('queue'):
            queue = args['queue']
            if queue not in queues:
                raise cherrypy.HTTPError(400, "queue name not found")
        else:
            raise cherrypy.HTTPError(400, "JSON missing `queue` key")

        # check for kwargs
        if args.has_key('kwargs'):
            kwargs = args['kwargs']
        else:
            kwargs = None

        # check for args
        if args.has_key('args'):
            args = args['args']
        else:
            args = None

        # If no arguments specified, fail
        if not args and not kwargs:
            raise cherrypy.HTTPError(400, "No task arguments specified")

        # Submit task
        task_obj = send_task( function, args=args, kwargs=kwargs, queue=queue, track_started=True)
        user = check_user(cherrypy.request.login)

        task_log = {
                'task_id':task_obj.task_id,
                'user':user,
                'task_name':function,
                'args':args,
                'kwargs':kwargs,
                'queue':queue,
                'timestamp':datetime.now()
        }
        self.db[self.database][self.collection].insert(task_log)        


        task_return = json.dumps({"task_id": task_obj.task_id})
        if GETargs.has_key("callback"):
            callback = GETargs['callback']
            return "%s(%s)" % (str(callback), task_return)
        else:
            return task_return

    @cherrypy.expose 
    def list(self):
        """ List available tasks """
        cherrypy.response.headers['Content-Type'] = "application/json"
        return json.dumps(list_tasks(), indent=1)

    @cherrypy.expose
    def status(self,task_id=None):
        """ GET """
        col = self.db[self.database][self.tomb_collection]
        user = check_user(cherrypy.request.login)
        if task_id:
            result = [ item for item in col.find({'_id': task_id}) ]
            cherrypy.response.headers['Content-Type'] = "application/json"
            return json.dumps({"status": result[0]['status']}, default=handler, indent=1)
        else:
            return json.dumps({"error": "please specify a valid task_id"})
 
    @cherrypy.expose
    def result(self,task_id=None):
        """ GET """
        col = self.db[self.database][self.tomb_collection]
        user = check_user(cherrypy.request.login)
        if task_id:
            result = [ item for item in col.find({'_id': task_id}) ]
            cherrypy.response.headers['Content-Type'] = "application/json"
            return json.dumps({"result": pickle.loads(result[0]['result'])}, default=handler, indent=1)

    @cherrypy.expose
    def reset(self):
        """ Reset list of tasks, clearing memcache """ 
        cherrypy.response.headers['Content-Type'] = "application/json"
        return json.dumps(reset_tasks(check_user(cherrypy.request.login)), indent=1)

    @cherrypy.expose
    def history(self, task_name=None, limit=50):
        """ Show a history of tasks """
        limit = int(limit)
        col = self.db[self.database][self.collection]
        user = check_user(cherrypy.request.login)
        if task_name:
            # return all tasks for given user and task_name
            history = [ item for item in col.find({'task_name': task_name, 'user': user},limit=limit) ] 
            cherrypy.response.headers['Content-Type'] = "application/json"
            return json.dumps(history,indent=1,default=handler)
        else:
            # return all tasks for a given user
            history = [ item for item in col.find({'user':user}, limit=limit) ]
            cherrypy.response.headers['Content-Type'] = "application/json"
            return json.dumps(history, indent=1, default=handler)



cherrypy.tree.mount(Root())
application = cherrypy.tree

if __name__ == '__main__':
    cherrypy.engine.start()
    cherrypy.engine.block()  

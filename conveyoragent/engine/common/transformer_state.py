# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# Copyright 2014 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from conveyoragent.engine.common import transformer
from conveyoragent.common import log as logging
from conveyoragent import exception
LOG = logging.getLogger(__name__)

_task_map = {}

class TransformerSate(object):
    
    def __new__(cls,*args,**kwargs): 
        if not hasattr(cls,'_inst'): 
            cls._inst=super(TransformerSate,cls).__new__(cls,*args,**kwargs) 
        return cls._inst
    
    def update_state(self, task_id, state):
        task = _task_map.get(task_id)
        
        if not task:
            task = transformer.TransformerTask(task_id=id, task_state=state)
            self.add_task(task)
        else:
            task.task_state = state
            
    
    def remove(self, task_id):
        task = _task_map.get(task_id)
        if not task:
            LOG.error("remove transformer task error: task is not exist")
            msg = "Remove transformer task is not exist"
            raise exception.V2vException(message=msg)
        
        _task_map.pop(task_id)
    
    def add_task(self, task):
        
        if not task:
            LOG.error("Add transformer task error: add task is null")
            msg = "add transformer task is null"
            raise exception.V2vException(message=msg)
    
        task_id = task.id
        
        exist_task = _task_map.get(task_id)
        
        if exist_task:
            LOG.error("Add transformer task error: add task is exist")
            msg = "add transformer task is exist"
            raise exception.V2vException(message=msg)
        
        _task_map[task_id] = task
        
    def get_task_state(self, task_id):
        
        task = _task_map.get(task_id)
        if not task:
            LOG.error("Query transformer task state error: task is not exist")
            msg = "Query transformer task state is not exist"
            raise exception.V2vException(message=msg)
        
        return task.task_state
        
if __name__ == '__main__':
    
    a = TransformerSate()
    t1 = transformer.TransformerTask(task_id="1", task_state='transformer')
    a.add_task(t1)
    b = TransformerSate()
    t2 = transformer.TransformerTask(task_id="2", task_state='transformer')
    b.add_task(t2)
    a.update_state("2", "finished")
    b.update_state("1", "error")
    print _task_map.keys()
    for key, task in _task_map.items():
        print("test: %s", task.task_state)
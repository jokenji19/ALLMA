"""Track persisted row and JSON-container changes without scanning old turns."""
from copy import deepcopy
from uuid import uuid4
import weakref


def observe(value, changed, lock):
    if isinstance(value, dict):
        return ObservedDict(value, changed, lock)
    if isinstance(value, list):
        return ObservedList(value, changed, lock)
    return value


class ObservedDict(dict):
    def __init__(self, values, changed, lock):
        self.changed, self.guard = changed, lock
        dict.__init__(self,((key,observe(value,changed,lock)) for key,value in values.items()))

    def __setitem__(self,key,value):
        with self.guard:
            dict.__setitem__(self,key,observe(value,self.changed,self.guard));self.changed()

    def __delitem__(self,key):
        with self.guard:
            dict.__delitem__(self,key);self.changed()

    def update(self,*args,**kwargs):
        with self.guard:
            for key,value in dict(*args,**kwargs).items():self[key]=value

    def setdefault(self,key,default=None):
        with self.guard:
            if key not in self:self[key]=default
            return self[key]

    def pop(self,key,*default):
        with self.guard:
            existed=key in self;value=dict.pop(self,key,*default)
            if existed:self.changed()
            return value

    def popitem(self):
        with self.guard:
            value=dict.popitem(self);self.changed();return value

    def clear(self):
        with self.guard:
            dict.clear(self);self.changed()

    def __ior__(self,other):
        self.update(other);return self

    def __deepcopy__(self,memo):
        return {deepcopy(k,memo):deepcopy(v,memo) for k,v in self.items()}


class ObservedList(list):
    def __init__(self, values, changed, lock):
        self.changed,self.guard=changed,lock
        list.__init__(self,(observe(v,changed,lock) for v in values))

    def __setitem__(self,key,value):
        with self.guard:
            value=([observe(v,self.changed,self.guard) for v in value] if isinstance(key,slice)
                   else observe(value,self.changed,self.guard))
            list.__setitem__(self,key,value);self.changed()

    def __delitem__(self,key):
        with self.guard:list.__delitem__(self,key);self.changed()

    def append(self,value):
        with self.guard:list.append(self,observe(value,self.changed,self.guard));self.changed()

    def extend(self,values):
        with self.guard:
            list.extend(self,[observe(v,self.changed,self.guard) for v in values]);self.changed()

    def insert(self,index,value):
        with self.guard:list.insert(self,index,observe(value,self.changed,self.guard));self.changed()

    def pop(self,index=-1):
        with self.guard:
            value=list.pop(self,index);self.changed();return value

    def remove(self,value):
        with self.guard:list.remove(self,value);self.changed()

    def clear(self):
        with self.guard:list.clear(self);self.changed()

    def reverse(self):
        with self.guard:list.reverse(self);self.changed()

    def sort(self,*args,**kwargs):
        with self.guard:list.sort(self,*args,**kwargs);self.changed()

    def __iadd__(self,values):
        self.extend(values);return self

    def __imul__(self,count):
        with self.guard:list.__imul__(self,count);self.changed();return self

    def __deepcopy__(self,memo):
        return [deepcopy(value,memo) for value in self]


class PersistedRow:
    def _watch(self,changed,lock):
        object.__setattr__(self,'_observer',changed)
        object.__setattr__(self,'_observer_lock',lock)
        object.__setattr__(self,'metadata',observe(self.metadata,changed,lock))

    def _unwatch(self):
        object.__setattr__(self,'metadata',deepcopy(self.metadata))
        object.__setattr__(self,'_observer',None)
        object.__setattr__(self,'_observer_lock',None)

    def __setattr__(self,name,value):
        lock=self.__dict__.get('_observer_lock')
        if name.startswith('_') or lock is None:
            object.__setattr__(self,name,value);return
        with lock:
            changed=self.__dict__['_observer']
            if name=='metadata':value=observe(value,changed,lock)
            object.__setattr__(self,name,value)
            if name!='embeddings':changed()

    def __deepcopy__(self,memo):
        return type(self)(**{key:deepcopy(getattr(self,key),memo) for key in self.__dataclass_fields__})


class RowList(list):
    def __init__(self,values,changes,kind,owner=None):
        self.changes,self.kind,self.owner=changes,kind,owner
        list.__init__(self)
        self.extend(values)

    def append(self,value):
        with self.changes.memory.lock:
            list.append(self,self.changes.attach(value,self.kind,self.owner))

    def extend(self,values):
        with self.changes.memory.lock:
            for value in list(values):self.append(value)

    def pop(self,index=-1):
        with self.changes.memory.lock:
            value=list.pop(self,index);self.changes.detach(value,self.kind);return value

    def clear(self):
        with self.changes.memory.lock:
            for value in self:self.changes.detach(value,self.kind)
            list.clear(self)

    def remove(self,value):
        self.pop(self.index(value))

    def _replace(self,values):
        self.clear();self.extend(values)
        for position,value in enumerate(self):
            value._archive_position=position
            self.changes.dirty[self.kind][value._archive_key]=value
        self.changes.positions[self.kind,self.owner]=len(self)

    def __setitem__(self,key,value):
        with self.changes.memory.lock:
            values=list(self);values[key]=value;self._replace(values)

    def __delitem__(self,key):
        with self.changes.memory.lock:
            values=list(self);del values[key];self._replace(values)

    def insert(self,index,value):
        with self.changes.memory.lock:
            values=list(self);values.insert(index,value);self._replace(values)

    def reverse(self):
        with self.changes.memory.lock:self._replace(list(reversed(self)))

    def sort(self,*args,**kwargs):
        with self.changes.memory.lock:
            values=list(self);values.sort(*args,**kwargs);self._replace(values)

    def __iadd__(self,values):
        self.extend(values);return self

    def __imul__(self,count):
        with self.changes.memory.lock:self._replace(list(self)*count);return self

    def __deepcopy__(self,memo):
        return [deepcopy(value,memo) for value in self]


class ConversationGroups(dict):
    def __init__(self,values,changes):
        self.changes=changes
        dict.__init__(self)
        for owner,rows in values.items():self[owner]=rows

    def __missing__(self,owner):
        self[owner]=[];return self[owner]

    def __setitem__(self,owner,rows):
        with self.changes.memory.lock:
            if dict.get(self,owner) is rows:return
            from .paged_history import PagedRows
            if isinstance(rows,PagedRows):
                dict.__setitem__(self,owner,rows)
            elif owner in self and isinstance(dict.__getitem__(self,owner),PagedRows):
                self[owner].replace_all(list(rows))
            elif getattr(self.changes.memory,'_history_store',None) is not None:
                from .conversational_memory import Conversation
                page=PagedRows(self.changes.memory._history_store,self.changes,'conversations',Conversation,owner)
                page.extend(rows);dict.__setitem__(self,owner,page)
            else:
                rows=list(rows)
                if owner in self:dict.__getitem__(self,owner).clear()
                dict.__setitem__(self,owner,RowList(rows,self.changes,'conversations',owner))
            self.changes.sections.add('conversation_users')

    def __delitem__(self,owner):
        with self.changes.memory.lock:
            dict.__getitem__(self,owner).clear();dict.__delitem__(self,owner)
            self.changes.sections.add('conversation_users')

    def setdefault(self,owner,default=None):
        if owner not in self:self[owner]=default or []
        return self[owner]

    def update(self,*args,**kwargs):
        for owner,rows in dict(*args,**kwargs).items():self[owner]=rows

    def pop(self,owner,*default):
        if owner not in self:
            if default:return default[0]
            raise KeyError(owner)
        value=list(self[owner]);del self[owner];return value

    def clear(self):
        for owner in list(self):del self[owner]

    def popitem(self):
        if not self:raise KeyError('empty conversation groups')
        owner=next(reversed(self));return owner,self.pop(owner)

    def __ior__(self,other):
        self.update(other);return self


class HistoryChanges:
    def __init__(self,memory):
        self.memory=memory
        self.dirty={'messages':{},'conversations':{}}
        self.deleted={'messages':set(),'conversations':set()}
        self.live={kind:weakref.WeakValueDictionary() for kind in ('messages','conversations')}
        self.touched={}
        self.persisted={'messages':set(),'conversations':set()}
        self.sections=set()
        self.deleted_counts={}
        self.positions={}
        self.loading=True

    def attach(self,row,kind,owner,*,persisted=False):
        if not isinstance(row,PersistedRow):raise TypeError('History row must be a persisted record')
        if row.__dict__.get('_observer') is not None:row=deepcopy(row)
        key=row.__dict__.get('_archive_key') or uuid4().hex
        if key in self.live[kind]:
            row=deepcopy(row);key=uuid4().hex
        counter=self.positions.get((kind,owner),0)
        position=row.__dict__.get('_archive_position',counter) if self.loading or persisted else counter
        self.positions[kind,owner]=max(counter,position+1)
        row._archive_key,row._archive_position,row._archive_owner=key,position,owner
        self.live[kind][key]=row
        self.deleted[kind].discard(key)
        if kind=='messages':self.deleted_counts.pop(key,None)
        row._archive_persisted=self.loading or persisted or row.__dict__.get('_archive_persisted',False)
        if not self.loading and not persisted:self.dirty[kind][key]=row
        reference=weakref.ref(row)
        row._watch(lambda:self.mark(kind,key,reference()),self.memory.lock)
        return row

    def mark(self,kind,key,row):
        with self.memory.lock:
            if row is not None and self.live[kind].get(key) is row:self.dirty[kind][key]=row

    def detach(self,row,kind):
        key=row._archive_key
        self.live[kind].pop(key,None);self.dirty[kind].pop(key,None)
        if row.__dict__.get('_archive_persisted',False):
            self.deleted[kind].add(key)
            if kind=='messages':self.deleted_counts[key]=row.__dict__.get('_archive_count_key')
        row._unwatch()

    def replace(self,name,values,old=None):
        if values is old:return values
        if name=='messages':
            from .paged_history import PagedRows
            if isinstance(old,PagedRows):
                old.replace_all(list(values));return old
            values=list(values)
            if isinstance(old,RowList):old.clear()
            return RowList(values,self,'messages')
        if name=='conversations':
            values={owner:list(rows) for owner,rows in values.items()}
            if isinstance(old,ConversationGroups):old.clear()
            return ConversationGroups(values,self)
        self.sections.add(name)
        return observe(values,lambda:self.sections.add(name),self.memory.lock)

    def committed(self):
        for kind in self.dirty:
            for row in self.dirty[kind].values():row._archive_persisted=True
            self.dirty[kind].clear();self.deleted[kind].clear()
        self.sections.clear()
        self.deleted_counts.clear()
        for page in self.touched.values():page.committed()
        self.touched.clear()

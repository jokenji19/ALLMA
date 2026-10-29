"""Mutable archive sequences with bounded read caches and durable full access.

Ordinary reads stream pages. Explicit structural edits (sort/slice replacement,
remove/reorder) materialize that sequence until its transaction commits. Dirty
rows are pinned by HistoryChanges, so cache eviction can never discard an edit.
"""
from collections import OrderedDict
from collections.abc import MutableSequence
from copy import deepcopy
from itertools import zip_longest

from .history_changes import RowList


class PagedRows(MutableSequence):
    PAGE_SIZE=64
    CACHE_SIZE=128

    def __init__(self,store,changes,kind,constructor,owner=None,count=0,last=-1):
        self.store,self.changes,self.kind,self.constructor,self.owner=store,changes,kind,constructor,owner
        self._count,self._last=count,last
        self.cache=OrderedDict()
        self.pending=RowList([],changes,kind,owner)
        self.materialized=None
        self._epoch=0
        changes.positions[kind,owner]=last+1

    def __len__(self):
        if self.materialized is not None:return len(self.materialized)
        return self._count+len(self.pending)

    def _row(self,raw,index):
        token,position,data=raw
        row=self.changes.live[self.kind].get(token)
        if row is None:
            from datetime import datetime
            data=dict(data);data.setdefault('metadata',{})
            data['timestamp']=datetime.fromisoformat(data['timestamp'])
            row=self.constructor(**{key:data.get(key) for key in self.store.FIELDS[self.kind]})
            row._archive_key,row._archive_position=token,position
            if self.kind=='messages':
                uid=row.user_id or row.metadata.get('user_id')
                row._archive_count_key=(uid if isinstance(uid,str) else None,row.role)
            row=self.changes.attach(row,self.kind,self.owner,persisted=True)
        self.cache[index]=row;self.cache.move_to_end(index)
        while len(self.cache)>self.CACHE_SIZE:self.cache.popitem(last=False)
        return row

    def preload(self,records):
        start=self._count-len(records)
        for index,raw in enumerate(records,start):self._row(raw,index)

    def __getitem__(self,index):
        with self.changes.memory.lock:
            if self.materialized is not None:return self.materialized[index]
            if isinstance(index,slice):
                start,stop,step=index.indices(len(self))
                return [self[i] for i in range(start,stop,step)]
            import operator
            index=operator.index(index)
            if index<0:index+=len(self)
            if not 0<=index<len(self):raise IndexError('history index out of range')
            if index>=self._count:return self.pending[index-self._count]
            if index in self.cache:
                row=self.cache[index];self.cache.move_to_end(index);return row
            start=index//self.PAGE_SIZE*self.PAGE_SIZE
            rows=self.store.page(self.kind,self.owner,start,min(self.PAGE_SIZE,self._count-start),self._count)
            for ordinal,raw in enumerate(rows,start):self._row(raw,ordinal)
            return self.cache[index]

    def __iter__(self):
        yield from self._iterate(False)

    def __reversed__(self):
        yield from self._iterate(True)

    def _check_read(self,epoch,generation):
        if (self._epoch!=epoch or self.store.generation!=generation
                or self.changes.memory._changes is not self.changes):
            from allma_model.utils.persistence import StateRecoveryRequired
            raise StateRecoveryRequired('History changed during iteration; restart the read')

    def _iterate(self,reverse):
        with self.changes.memory.lock:
            epoch,generation=self._epoch,self.store.generation
            count=self._count
            pending=tuple(self.pending)
            materialized=self.materialized
            length=len(materialized) if materialized is not None else 0
        if materialized is not None:
            for i in (range(length-1,-1,-1) if reverse else range(length)):
                with self.changes.memory.lock:
                    self._check_read(epoch,generation);row=materialized[i]
                yield row
            return
        def unsaved():
            for row in (reversed(pending) if reverse else pending):
                with self.changes.memory.lock:self._check_read(epoch,generation)
                yield row
        if reverse:yield from unsaved()
        for offset,raw in enumerate(self.store.stream(self.kind,self.owner,reverse=reverse)):
            with self.changes.memory.lock:
                self._check_read(epoch,generation)
                if offset>=count:break
                row=self._row(raw,count-1-offset if reverse else offset)
            yield row
        with self.changes.memory.lock:self._check_read(epoch,generation)
        if not reverse:yield from unsaved()

    def append(self,value):
        with self.changes.memory.lock:
            (self.materialized if self.materialized is not None else self.pending).append(value)
            self._epoch+=1
            self.changes.touched[id(self)]=self

    def extend(self,values):
        with self.changes.memory.lock:
            # Aliases and generators may read this same sequence.
            for value in list(values):self.append(value)

    def _all(self):
        if self.materialized is None:
            values=list(self)
            rows=RowList([],self.changes,self.kind,self.owner)
            # Existing rows already belong to these observers; adopt references
            # rather than cloning them or registering duplicate archive keys.
            list.extend(rows,values)
            self.materialized=rows
            self.pending=RowList([],self.changes,self.kind,self.owner)
            self.cache.clear()
        self._epoch+=1
        self.changes.touched[id(self)]=self
        return self.materialized

    def replace_all(self,values):
        with self.changes.memory.lock:self._all()._replace(list(values))

    def __setitem__(self,key,value):
        with self.changes.memory.lock:self._all()[key]=value

    def __delitem__(self,key):
        with self.changes.memory.lock:del self._all()[key]

    def insert(self,index,value):
        with self.changes.memory.lock:self._all().insert(index,value)

    def pop(self,index=-1):
        with self.changes.memory.lock:
            ordinal=index if index>=0 else len(self)+index
            if self.materialized is None and self._count<=ordinal<len(self):
                self.changes.touched[id(self)]=self
                self._epoch+=1
                return self.pending.pop(ordinal-self._count)
            return self._all().pop(index)

    def clear(self):
        with self.changes.memory.lock:self._all().clear()

    def remove(self,value):
        with self.changes.memory.lock:self._all().remove(value)

    def reverse(self):
        with self.changes.memory.lock:self._all().reverse()

    def sort(self,*args,**kwargs):
        with self.changes.memory.lock:self._all().sort(*args,**kwargs)

    def __iadd__(self,values):
        self.extend(values);return self

    def __imul__(self,count):
        with self.changes.memory.lock:self._all().__imul__(count);return self

    def __eq__(self,other):
        if other is self:return True
        if not hasattr(other,'__iter__'):return False
        sentinel=object()
        return all(a==b for a,b in zip_longest(self,other,fillvalue=sentinel))

    def __deepcopy__(self,memo):
        return [deepcopy(row,memo) for row in self]

    def committed(self):
        self._epoch+=1
        if self.materialized is not None:
            count=len(self.materialized)
            tail=list(enumerate(self.materialized[max(0,count-self.CACHE_SIZE):],max(0,count-self.CACHE_SIZE)))
        else:
            count=self._count+len(self.pending)
            tail=sorted([*self.cache.items(),*enumerate(self.pending,self._count)])[-self.CACHE_SIZE:]
        self._count=count
        self._last=self.changes.positions.get((self.kind,self.owner),0)-1
        self.materialized=None
        self.pending=RowList([],self.changes,self.kind,self.owner)
        self.cache=OrderedDict(tail)


class HistorySelection:
    """Repeatable filtered stream; retaining the view does not retain its rows."""
    def __init__(self,rows,predicate):self.rows,self.predicate=rows,predicate
    def __iter__(self):return (row for row in self.rows if self.predicate(row))
    def __reversed__(self):return (row for row in reversed(self.rows) if self.predicate(row))


def recent_rows(rows,limit,*,predicate=None):
    """Bounded adapter shared by canonical memory and compatibility readers."""
    from allma_model.core.autobiographical_identity import delivery_visible
    if type(limit) is not int or limit<0:raise ValueError('Invalid history limit')
    if not limit:return []
    result=[]
    for row in reversed(rows):
        if delivery_visible(row.metadata) and (predicate is None or predicate(row)):
            result.append(row)
            if len(result)==limit:break
    result.reverse()
    return result

"""Fixed synthetic challenges for durable learned answers; no model or personal data."""
import json
from unittest.mock import patch

from allma_model.learning_system.answer_recall import AnswerRecall
from allma_model.utils.persistence import StateRecoveryRequired
from memory_recovery_battery import run_challenges

CASES = []
QUESTION = 'Spiega il significato della luce bianca.'
ANSWER = 'La luce bianca contiene diversi colori.'


def case(name, criterion):
    def register(function):
        CASES.append(('learned_answers',name,criterion,function))
        return function
    return register


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def open_store(path, *, allow_error=False):
    store=AnswerRecall(path/'answer_recall.db', legacy_path=path/'answer_recall.json')
    if store.load_error is not None:
        # Synthetic diagnostic only: record the initialization cause instead
        # of mistaking several downstream failures for independent defects.
        error=store.load_error
        print('ALLMA_RECALL_STORAGE_INIT_ERROR '+json.dumps(
            {'type':type(error).__name__,'errno':getattr(error,'errno',None),'detail':str(error)}),flush=True)
        if not allow_error:
            raise AssertionError('Synthetic store initialization failed: '+type(error).__name__+': '+str(error))
    return store


def seed(path, count=520):
    records={str(i):{'user':'u','question':QUESTION,'answer':ANSWER,'observations':1,
                    'confirmations':['one','two'] if i==0 else [],'rejected':False}
             for i in range(count)}
    data=json.dumps({'version':1,'records':records,'delivery_checkpoint':7})
    (path/'answer_recall.json').write_text(data)
    return data


@case('migration_and_growth','Confirmed learning and replay order survive more than 500 records')
def migration(path):
    original=seed(path)
    store=open_store(path)
    store.observe('new','u',QUESTION,ANSWER,'new',delivery_sequence=8)
    restored=open_store(path)
    require(restored.lookup('0','u') is not None,'Confirmed answer lost')
    require(len(restored.records)==521 and restored.delivery_checkpoint==8,'Archive or checkpoint lost')
    require((path/'answer_recall.json').read_text()==original,'Migration changed original archive')


@case('bounded_cache','RAM eviction does not delete durable answers')
def cache(path):
    seed(path)
    store=open_store(path)
    for i in range(520):
        require(store.records[str(i)]['user']=='u','Archive row missing')
    require(len(store._store.cache)==500 and '0' not in store._store.cache,'Cache is not bounded')
    require(store.lookup('0','u') is not None,'Eviction deleted learning')


@case('revocation_and_isolation','Revocation invalidates another cache and cannot cross owners')
def revocation(path):
    seed(path,1)
    first=open_store(path);second=open_store(path)
    require(second.lookup('0','u') is not None,'Confirmed source unavailable')
    require(second.lookup('0','other') is None,'Wrong owner received an answer')
    require(not second.feedback('0','other','attack',False),'Wrong owner changed an answer')
    first.feedback('0','u','revoke',False)
    require(second.lookup('0','u') is None and open_store(path).lookup('0','u') is None,'Revocation was lost')


@case('failed_save_and_replay','Interrupted write cannot advance the learning checkpoint or duplicate an observation')
def replay(path):
    seed(path,1);store=open_store(path)
    with patch.object(store,'_save',side_effect=OSError('synthetic full disk')):
        try:
            store.observe('new','u',QUESTION,ANSWER,'new',delivery_sequence=8)
        except OSError:
            pass
        else:
            raise AssertionError('Failed write was accepted')
    require(open_store(path).delivery_checkpoint==7 and 'new' not in store.records,'Failed write published learning')
    store.observe('new','u',QUESTION,ANSWER,'new',delivery_sequence=8)
    store.observe('new','u',QUESTION,ANSWER,'replay',delivery_sequence=8)
    require(open_store(path).records['new']['observations']==1,'Replayed observation counted twice')


@case('interrupted_migration','An interrupted publication preserves legacy bytes and can be resumed')
def interrupted(path):
    original=seed(path,1)
    with patch('allma_model.learning_system.recall_store.os.replace',side_effect=OSError('synthetic publication failure')):
        failed=open_store(path,allow_error=True)
    require(failed.load_error is not None and not failed.path.exists(),'Partial archive published')
    require((path/'answer_recall.json').read_text()==original,'Original lost')
    require(open_store(path).lookup('0','u') is not None,'Migration could not resume')


@case('changed_answer','A new candidate answer does not inherit old confirmations')
def changed(path):
    seed(path,1);store=open_store(path)
    store.observe('0','u',QUESTION,'Una risposta differente.','new',delivery_sequence=8)
    require(open_store(path).lookup('0','u') is None,'New answer inherited confirmations')
    require(open_store(path).records['0']['confirmations']==[],'Old confirmation retained')


@case('backup_roundtrip','Backup includes the durable store and restores revocations and checkpoints')
def backup(path):
    from allma_model.utils.state_backup import StateBackups,verify_archive
    seed(path,1);store=open_store(path)
    require(store.feedback('0','u','revoke',False),'Revocation was not stored')
    snapshots=StateBackups(path);created=snapshots.create()
    destination=path/'restored';destination.mkdir()
    manifest=verify_archive(snapshots.directory/created['id'],destination)
    require('answer_recall.db' in manifest['files'],'Learning database missing from backup')
    restored=open_store(destination)
    require(restored.records['0']['rejected'] and restored.delivery_checkpoint==7,'Restore changed learning state')


@case('corruption_no_rollback','A damaged live archive disables recall instead of reviving outdated legacy answers')
def corruption(path):
    seed(path,1);store=open_store(path)
    require(store.feedback('0','u','revoke',False),'Revocation was not stored')
    store.path.write_bytes(b'{synthetic damaged database')
    require(store.lookup('0','u') is None and store.load_error is not None,'Damage was not contained')
    require(open_store(path,allow_error=True).lookup('0','u') is None,'Outdated legacy answer revived')
    try:
        store.observe('new','u',QUESTION,ANSWER,'new')
    except StateRecoveryRequired:
        pass
    else:
        raise AssertionError('Damaged archive was overwritten')


def run_battery(output, *, scope=None, cancel_event=None, progress_callback=None):
    require(len(CASES)==8,'Unexpected learned-answer challenge plan')
    return run_challenges(output,CASES,version='learned-answer-storage-v1',scope=scope,
        cancel_event=cancel_event,progress_callback=progress_callback,harness_path=__file__)

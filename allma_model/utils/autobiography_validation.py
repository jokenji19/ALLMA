"""Read-only format checks shared by backup import and longevity challenges."""
from datetime import datetime


def validate_history_record(kind,record):
    """Check one decoded row, without constructing a synthetic archive root."""
    if kind=='conversations':
        if (not isinstance(record,dict) or not isinstance(record.get('id'),str)
                or not isinstance(record.get('user_id'),str) or not isinstance(record.get('content'),str)
                or not isinstance(record.get('metadata'),dict)):
            raise ValueError('Invalid conversation record')
    elif kind=='messages':
        if (not isinstance(record,dict) or record.get('role') not in ('user','assistant','system')
                or not isinstance(record.get('content'),str) or not isinstance(record.get('metadata',{}),dict)
                or not isinstance(record.get('conversation_id'),str)):
            raise ValueError('Invalid autobiographical record')
    else:raise ValueError('Unknown history collection')
    return datetime.fromisoformat(record['timestamp'])


def validate_history_archive(data):
    if (not isinstance(data,dict) or not isinstance(data.get('messages',[]),list)
            or not isinstance(data.get('conversations',{}),dict) or not isinstance(data.get('user_data',{}),dict)):
        raise ValueError('Invalid autobiographical archive')
    if not isinstance(data.get('trauma_log',[]),list):
        raise ValueError('Invalid autobiographical metadata')
    for rows in data.get('conversations',{}).values():
        if not isinstance(rows,list):raise ValueError('Invalid conversation list')
        for row in rows:
            validate_history_record('conversations',row)
    for record in data.get('messages',[]):
        validate_history_record('messages',record)

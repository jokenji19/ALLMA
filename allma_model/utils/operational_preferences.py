"""Portable preferences, without model weights or Android permission grants."""
import math

FILES=('model_binding.json','notifications.json')
MAX_BYTES=64*1024
NOTIFICATION_EVENTS=frozenset(('message','dream','model','test'))


def validate_model_preference(data):
    if (not isinstance(data,dict) or type(data.get('version')) is not int
            or data['version']!=1 or not set(data)<= {'version','model_name','reasoning'}):
        raise ValueError('Preferenza del modello non supportata')
    name=data.get('model_name')
    if (not isinstance(name,str) or not name.endswith('.gguf') or len(name)>255
            or name in ('.gguf','..gguf') or any(c in name for c in ('/','\\',':'))
            or any(ord(c)<32 for c in name)):
        raise ValueError('Nome del modello non valido')
    if data.get('reasoning') is not None and type(data['reasoning']) is not bool:
        raise ValueError('Preferenza di ragionamento non valida')
    return data


def validate_notification_preference(data):
    if (not isinstance(data,dict) or type(data.get('version')) is not int
            or data['version']!=1 or type(data.get('enabled')) is not bool
            or not set(data)<= {'version','enabled','last_sent'}):
        raise ValueError('Preferenza delle notifiche non supportata')
    sent=data.get('last_sent',{})
    if (not isinstance(sent,dict) or not set(sent)<=NOTIFICATION_EVENTS
            or any(type(value) not in (int,float) or not 0<=value<2**53 or not math.isfinite(value)
                   for value in sent.values())):
        raise ValueError('Tempi delle notifiche non validi')
    return data


def validate_preference(name,data):
    return (validate_model_preference if name=='model_binding.json'
            else validate_notification_preference)(data)

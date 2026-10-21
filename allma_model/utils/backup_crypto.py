"""Versioned, bounded-memory authenticated backup encryption.

PBKDF2 derives one AES-256 key. Each record has a unique nonce and authenticates
the public header, its position and final-record flag. Missing/reordered records,
wrong passwords and extra bytes fail before any restore is published.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import threading

from .persistence import sync_directory

MAGIC=b'ALLMA-BACKUP-1\n'
ITERATIONS=600_000
CHUNK=256*1024
MAX_ARCHIVE=4*1024**3


class BackupCryptoError(ValueError):
    pass


class DesktopCipher:
    def __init__(self,key):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        self.cipher=AESGCM(key)

    def encrypt(self,nonce,data,aad):
        return self.cipher.encrypt(nonce,data,aad)

    def decrypt(self,nonce,data,aad):
        return self.cipher.decrypt(nonce,data,aad)


_android_helper=None


def android_cipher_helper():
    global _android_helper
    if _android_helper is not None:return _android_helper
    # JNI FindClass on a Python-created worker uses the system classloader.
    # Resolve the application class on Android's UI thread once; encryption
    # itself always stays on the worker and never blocks UI rendering.
    from android.runnable import run_on_ui_thread
    ready=threading.Event();result=[];errors=[]
    @run_on_ui_thread
    def load():
        try:
            from jnius import autoclass
            result.append(autoclass('org.allma.backup.BackupCipher'))
        except Exception as error:errors.append(error)
        finally:ready.set()
    load()
    if not ready.wait(10):raise BackupCryptoError('Supporto di cifratura Android non pronto. Riprova.')
    if errors:raise BackupCryptoError('Supporto di cifratura Android non disponibile') from errors[0]
    _android_helper=result[0]
    return _android_helper


class AndroidCipher:
    def __init__(self,key):
        self.helper=android_cipher_helper()
        self.key=key

    def _run(self,mode,nonce,data,aad):
        return bytes(int(value)&255 for value in self.helper.crypt(mode,self.key,nonce,data,aad))

    def encrypt(self,nonce,data,aad):
        return self._run(1,nonce,data,aad)

    def decrypt(self,nonce,data,aad):
        return self._run(2,nonce,data,aad)


def cipher_factory(key):
    if 'ANDROID_PRIVATE' in os.environ or 'ANDROID_ARGUMENT' in os.environ:
        return AndroidCipher(key)
    return DesktopCipher(key)


def _password(value):
    if not isinstance(value,str) or not 12 <= len(value) <= 1024:
        raise BackupCryptoError('Usa una password di almeno 12 caratteri e conservala: non posso recuperarla.')
    return value.encode('utf-8')


def _read_exact(handle,size):
    data=handle.read(size)
    if len(data)!=size:
        raise BackupCryptoError('Backup incompleto o danneggiato')
    return data


def _record_aad(header,index,final):
    return header+struct.pack('>I?',index,final)


def _process(source,target,password,*,decrypt=False,factory=cipher_factory):
    source,target=Path(source),Path(target)
    if source.resolve()==target.resolve():
        raise BackupCryptoError('Origine e destinazione devono essere diverse')
    encoded_password=_password(password)
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.allma-crypto-',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as writer,source.open('rb') as reader:
            if decrypt:
                if _read_exact(reader,len(MAGIC))!=MAGIC:
                    raise BackupCryptoError('Formato di backup non riconosciuto')
                header_size=struct.unpack('>I',_read_exact(reader,4))[0]
                if not 1 <= header_size <= 4096:
                    raise BackupCryptoError('Intestazione del backup non valida')
                encoded=_read_exact(reader,header_size)
                header=json.loads(encoded)
                if (not isinstance(header,dict) or type(header.get('version')) is not int or header['version']!=1
                        or header.get('cipher')!='AES-256-GCM-CHUNKED'
                        or header.get('kdf')!='PBKDF2-HMAC-SHA256'
                        or type(header.get('iterations')) is not int or header['iterations']!=ITERATIONS
                        or type(header.get('chunk')) is not int or header['chunk']!=CHUNK
                        or type(header.get('size')) is not int or not 0 <= header['size'] <= MAX_ARCHIVE):
                    raise BackupCryptoError('Versione o parametri del backup non supportati')
                salt=base64.b64decode(header['salt'],validate=True)
                prefix=base64.b64decode(header['nonce'],validate=True)
                if len(salt)!=16 or len(prefix)!=8:
                    raise BackupCryptoError('Parametri di cifratura non validi')
            else:
                size=source.stat().st_size
                if not 0 <= size <= MAX_ARCHIVE:
                    raise BackupCryptoError('Archivio troppo grande per questo formato di esportazione')
                salt,prefix=os.urandom(16),os.urandom(8)
                header={'version':1,'cipher':'AES-256-GCM-CHUNKED','kdf':'PBKDF2-HMAC-SHA256',
                        'iterations':ITERATIONS,'chunk':CHUNK,'size':size,
                        'salt':base64.b64encode(salt).decode(),'nonce':base64.b64encode(prefix).decode()}
                encoded=json.dumps(header,sort_keys=True,separators=(',',':')).encode()
                writer.write(MAGIC+struct.pack('>I',len(encoded))+encoded)
            aad=MAGIC+encoded
            key=hashlib.pbkdf2_hmac('sha256',encoded_password,salt,ITERATIONS,32)
            backend=factory(key)
            remaining,index=header['size'],0
            while remaining:
                size=min(CHUNK,remaining)
                nonce=prefix+struct.pack('>I',index)
                if decrypt:
                    data=backend.decrypt(nonce,_read_exact(reader,size+16),_record_aad(aad,index,False))
                    if len(data)!=size:
                        raise BackupCryptoError('Lunghezza del backup non valida')
                else:
                    data=backend.encrypt(nonce,_read_exact(reader,size),_record_aad(aad,index,False))
                writer.write(data)
                remaining-=size
                index+=1
            nonce=prefix+struct.pack('>I',index)
            if decrypt:
                final=backend.decrypt(nonce,_read_exact(reader,16),_record_aad(aad,index,True))
                if final or reader.read(1):
                    raise BackupCryptoError('Backup incompleto o con dati aggiunti')
            else:
                if reader.read(1):
                    raise BackupCryptoError('Il file è cambiato durante la cifratura')
                writer.write(backend.encrypt(nonce,b'',_record_aad(aad,index,True)))
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary,target)
        sync_directory(target.parent)
        return str(target)
    except BackupCryptoError:
        raise
    except Exception as error:
        raise BackupCryptoError('Password errata, backup danneggiato o cifratura non disponibile') from error
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def encrypt_backup(source,target,password,**options):
    return _process(source,target,password,**options)


def decrypt_backup(source,target,password,**options):
    return _process(source,target,password,decrypt=True,**options)

"""Optional local HTTP adapter. Configure authentication before creating the app.

No server, core, database or demo account is created during module import.
"""
from functools import wraps
import json
import os
import threading
import time


def create_app(core=None, config=None):
    from flask import Flask, jsonify, request, g
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    from werkzeug.security import check_password_hash, generate_password_hash
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('ALLMA_API_SECRET'),
                      AUTH_USERS=json.loads(os.environ.get('ALLMA_API_USERS','{}')),
                      TOKEN_MAX_AGE=3600, MAX_CONTENT_LENGTH=128*1024)
    app.config.update(config or {})
    secret, users = app.config['SECRET_KEY'], app.config['AUTH_USERS']
    if (not isinstance(secret,str) or len(secret)<32 or not isinstance(users,dict) or not users
            or any(not isinstance(u,str) or not u or not isinstance(h,str)
                   or not h.startswith(('scrypt:','pbkdf2:')) for u,h in users.items())):
        raise ValueError('Configure ALLMA_API_SECRET and hashed ALLMA_API_USERS before enabling the HTTP adapter')
    from allma_model.api.allma_api import AllmaAndroidBridge
    bridge = AllmaAndroidBridge(core=core) if core is not None else AllmaAndroidBridge(
        db_path=app.config.get('ALLMA_DB_PATH',os.path.join(app.instance_path,'allma.db')))
    app.extensions['allma_bridge'] = bridge
    tokens = URLSafeTimedSerializer(secret,salt='allma-api-v1')
    dummy_hash = generate_password_hash('unused-dummy-password')
    attempts, lock = {}, threading.Lock()

    def authenticated(function):
        @wraps(function)
        def call(*args,**kwargs):
            header = request.headers.get('Authorization','')
            if not header.startswith('Bearer '):
                return jsonify(error='Authentication required'),401
            try:
                data = tokens.loads(header[7:],max_age=app.config['TOKEN_MAX_AGE'])
                owner = data.get('user_id')
                if owner not in users:
                    raise BadSignature('Unknown user')
            except (BadSignature,SignatureExpired,ValueError,AttributeError,TypeError):
                return jsonify(error='Invalid or expired token'),401
            g.user_id = owner
            return function(*args,**kwargs)
        return call

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data,dict):
            raise ValueError('JSON object required')
        return data

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)),400

    @app.errorhandler(PermissionError)
    def forbidden(error):
        return jsonify(error='Resource unavailable'),404

    @app.route('/api/auth/login',methods=['POST'])
    def login():
        data = body()
        username, password = data.get('username'), data.get('password')
        if not isinstance(username,str) or not isinstance(password,str):
            return jsonify(error='Invalid credentials'),401
        key, now = request.remote_addr, time.monotonic()
        with lock:
            count, started = attempts.get(key,(0,now))
            if now-started>60: count,started=0,now
            if count>=5: return jsonify(error='Retry later'),429
            if len(attempts)>=256 and key not in attempts: attempts.pop(next(iter(attempts)))
            attempts[key]=(count+1,started)
        valid = check_password_hash(users.get(username,dummy_hash),password)
        if not valid or username not in users:
            return jsonify(error='Invalid credentials'),401
        with lock: attempts.pop(key,None)
        return jsonify(access_token=tokens.dumps({'user_id':username}),token_type='Bearer')

    @app.route('/api/projects',methods=['GET','POST'])
    @authenticated
    def projects():
        if request.method=='POST':
            data=body()
            return jsonify(project_id=bridge.create_project(g.user_id,data.get('name'),
                data.get('description',''),data.get('metadata'))),201
        return jsonify([bridge.get_project_summary(p.id,user_id=g.user_id)
                        for p in bridge.project_tracker.get_user_projects(g.user_id)])

    @app.route('/api/projects/<project_id>')
    @authenticated
    def project(project_id):
        try:
            return jsonify(bridge.get_project_summary(project_id,user_id=g.user_id))
        except ValueError:
            return jsonify(error='Resource unavailable'),404

    @app.route('/api/conversation',methods=['POST'])
    @authenticated
    def conversation():
        data=body()
        return jsonify(bridge.process_message(g.user_id,data.get('message'),
                       {'session_id':data.get('conversation_id')}))

    @app.route('/api/emotional/state')
    @authenticated
    def emotional_state():
        return jsonify(bridge._emotional_state(g.user_id))

    @app.route('/api/learning/progress')
    @authenticated
    def progress():
        return jsonify(bridge.learner.get_learning_progress(g.user_id))

    @app.route('/api/dashboard/stats')
    @authenticated
    def stats():
        memory=bridge.allma.conversational_memory
        with memory.lock:
            conversations=len(memory.conversations.get(g.user_id,[]))
            messages=sum((m.user_id or m.metadata.get('user_id'))==g.user_id for m in memory.messages)
        return jsonify(projects={'total':len(bridge.project_tracker.get_user_projects(g.user_id))},
            emotional=bridge._emotional_state(g.user_id),learning=bridge.learner.get_learning_progress(g.user_id),
            conversation={'total':conversations,'messages':messages})
    return app


if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=5000,debug=False)

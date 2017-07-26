from flask import Flask, redirect, url_for, session, request, jsonify, abort
from flask_oauthlib.client import OAuth
import logging, redis

def create_client(app):
    logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s', level = logging.DEBUG, filename = 'oauth-client.log')
    oauth = OAuth(app)

    remote = oauth.remote_app(
        'CV Updater',
        consumer_key='SSPSN7CAU4QRALEVGGLCTK11R4SE3G151BCDBHSVP5VVH95DQU4JALH3KNK54NP2',
        consumer_secret='T7GE97EGJTJ6C42CEI9PA9S0KFMGLEHEEGT6PJV2T31AOLRT5C37VHV76SKP8SNN',
        request_token_params={'scope': 'email'},
        base_url='https://api.hh.ru',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://hh.ru/oauth/token',
        authorize_url='https://hh.ru/oauth/authorize'
    )
       
    @app.route('/')
    def index():
        if 'dev_token' in session:
            ret = remote.get('/api/me')
            return jsonify(ret.data)
        return redirect(url_for('login'))

    @app.route('/login')
    def login():
        return remote.authorize(callback=url_for('authorized', _external=True))

    @app.route('/logout')
    def logout():
        session.pop('dev_token', None)
        return redirect(url_for('index'))

    @app.route('/authorized', methods=['GET', 'POST'])
    def authorized():
        resp = remote.authorized_response()
        if resp is None:
            return 'Access denied: error=%s' % (
                request.args['error']
            )
        if isinstance(resp, dict) and 'access_token' in resp:
            #session['dev_token'] = (resp['access_token'], '')
            r = redis.Redis(unix_socket_path='/tmp/redis.sock')
            r.set('access_token', resp['access_token'])
            r.set('refresh_token', resp['refresh_token'])
            return jsonify(resp)
        return str(resp)
    
    @app.route('/me')
    def me():
        logging.info(session.get('dev_token'))
        ret = remote.get('/me')
        if ret.status not in (200, 201):
            return ret.raw_data, ret.status
        return ret.raw_data

    @app.route('/method/<name>')
    def method(name):
        func = getattr(remote, name)
        ret = func('method')
        return ret.raw_data

    @remote.tokengetter
    def get_oauth_token():
        return session.get('dev_token')

    return remote


if __name__ == '__main__':
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    # DEBUG=1 python oauth2_client.py
    app = Flask(__name__)
    app.debug = True
    app.secret_key = 'development'
    create_client(app)
    app.run(host='0.0.0.0', port=8000)

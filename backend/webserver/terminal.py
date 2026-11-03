"""Web terminal: an SSH session to the server (TERMINAL_SSH_HOST), relayed
over the page's socket. The user logs in with their own account on that
server each time; nothing is stored. Needs the "terminal" permission."""
import codecs
import logging
import threading
import time

from flask import request
from flask_login import current_user

from config import Config
from .sockets import socketio, authenticated_only

logger = logging.getLogger('gunicorn.error')

#: socket id -> session
SESSIONS = {}
_LOCK = threading.Lock()


class TermSession:
    def __init__(self, sid, username):
        self.sid = sid
        self.username = username
        self.client = None
        self.channel = None
        self.closed = False
        self.last_input = time.time()
        # input in the page's order: socket events may be handled in
        # parallel threads, so each carries a number
        self.next_seq = 0
        self.pending = {}
        self.input_lock = threading.Lock()

    def write(self, seq, text):
        with self.input_lock:
            if seq is None:  # no number: as it comes
                self.channel.send(text)
                return
            self.pending[seq] = text
            while self.next_seq in self.pending:
                self.channel.send(self.pending.pop(self.next_seq))
                self.next_seq += 1

    def close(self, reason=None):
        if self.closed:
            return
        self.closed = True
        for thing in (self.channel, self.client):
            try:
                if thing is not None:
                    thing.close()
            except Exception:
                pass
        socketio.emit('term_closed', {'reason': reason or ''}, to=self.sid)


def _connect(session, ssh_user, password, cols, rows):
    """Log in and relay the output (runs in its own thread)."""
    import paramiko
    host, port = Config.TERMINAL_SSH_HOST, Config.TERMINAL_SSH_PORT
    client = paramiko.SSHClient()
    # always this one configured host
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, port=port, username=ssh_user, password=password, timeout=10,
                       auth_timeout=15, banner_timeout=15, allow_agent=False, look_for_keys=False)
        channel = client.invoke_shell(term='xterm-256color', width=cols, height=rows)
    except paramiko.AuthenticationException:
        client.close()
        socketio.emit('term_error', {'code': 'auth'}, to=session.sid)
        _drop(session.sid, session)
        return
    except Exception as e:
        client.close()
        socketio.emit('term_error', {'code': 'connect', 'message': str(e)[:300]}, to=session.sid)
        _drop(session.sid, session)
        return
    if session.closed:  # the page went away meanwhile
        client.close()
        return
    session.client, session.channel = client, channel
    channel.settimeout(1.0)
    socketio.emit('term_ready', {'host': host, 'user': ssh_user}, to=session.sid)
    from .util import activity
    activity.record('terminal', _UserRef(session.username), detail={'ssh_user': ssh_user, 'host': host})

    decoder = codecs.getincrementaldecoder('utf-8')('replace')
    idle = Config.TERMINAL_IDLE_MINUTES * 60
    while not session.closed:
        try:
            data = channel.recv(32768)
        except Exception:  # timeout: check idle time, go on
            if idle and time.time() - session.last_input > idle:
                session.close('idle')
                break
            if channel.exit_status_ready() or channel.closed:
                break
            continue
        if not data:
            break
        socketio.emit('term_out', {'data': decoder.decode(data)}, to=session.sid)
    session.close('exit')
    _drop(session.sid, session)


class _UserRef:
    """activity.record wants a user object; the thread has no request user."""
    def __init__(self, username):
        self.username = username


def _drop(sid, session):
    with _LOCK:
        if SESSIONS.get(sid) is session:
            SESSIONS.pop(sid, None)


def close_for(sid):
    with _LOCK:
        session = SESSIONS.pop(sid, None)
    if session is not None:
        session.close('closed')


@socketio.on('term_open')
@authenticated_only
def term_open(data):
    if not Config.TERMINAL_ENABLED:
        return {'ok': False, 'code': 'disabled'}
    if not current_user.has_perm('terminal'):
        return {'ok': False, 'code': 'permission'}
    data = data if isinstance(data, dict) else {}
    ssh_user = str(data.get('username') or '').strip()
    password = str(data.get('password') or '')
    if not ssh_user:
        return {'ok': False, 'code': 'username'}
    try:
        cols = max(20, min(int(data.get('cols') or 100), 500))
        rows = max(5, min(int(data.get('rows') or 30), 200))
    except (TypeError, ValueError):
        cols, rows = 100, 30
    sid = request.sid
    close_for(sid)  # one session per page
    session = TermSession(sid, current_user.username)
    with _LOCK:
        SESSIONS[sid] = session
    threading.Thread(target=_connect, args=(session, ssh_user, password, cols, rows),
                     name=f"term-{sid}", daemon=True).start()
    return {'ok': True}


@socketio.on('term_in')
@authenticated_only
def term_in(data):
    session = SESSIONS.get(request.sid)
    if session is None or session.channel is None or not isinstance(data, dict):
        return
    session.last_input = time.time()
    try:
        seq = data.get('seq')
        session.write(int(seq) if isinstance(seq, int) else None, str(data.get('data') or ''))
    except Exception:
        session.close('error')


@socketio.on('term_resize')
@authenticated_only
def term_resize(data):
    session = SESSIONS.get(request.sid)
    if session is None or session.channel is None or not isinstance(data, dict):
        return
    try:
        session.channel.resize_pty(width=max(20, min(int(data.get('cols')), 500)),
                                   height=max(5, min(int(data.get('rows')), 200)))
    except Exception:
        pass


@socketio.on('term_close')
@authenticated_only
def term_close(data=None):
    close_for(request.sid)

"""Web terminal: SSH relay over the socket, against a small test SSH server."""
import socket
import threading
import time

import paramiko
import pytest

from webserver.util.passwords import hash_password


class _Server(paramiko.ServerInterface):
    def __init__(self):
        self.shell = threading.Event()

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL if (username, password) == ("ops", "right") else paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, *args):
        return True

    def check_channel_shell_request(self, channel):
        self.shell.set()
        return True

    def check_channel_window_change_request(self, *args):
        return True


@pytest.fixture(scope="module")
def ssh_server():
    key = paramiko.RSAKey.generate(2048)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(5)
    port = sock.getsockname()[1]

    def handle(conn):
        t = paramiko.Transport(conn)
        t.add_server_key(key)
        server = _Server()
        try:
            t.start_server(server=server)
        except Exception:
            return
        chan = t.accept(10)
        if chan is None:
            return
        server.shell.wait(5)
        chan.send("welcome 歡迎\r\n$ ")
        while True:
            data = chan.recv(1024)
            if not data:
                break
            if data.strip() == b"exit":
                chan.close()
                break
            chan.send(b"echo:" + data.upper())

    def accept():
        while True:
            try:
                conn, _ = sock.accept()
            except OSError:
                return
            threading.Thread(target=handle, args=(conn,), daemon=True).start()

    threading.Thread(target=accept, daemon=True).start()
    yield port
    sock.close()


def _login(username, role=None):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username, is_admin=False, role=role).save()
    c = app.test_client()
    assert c.post("/api/user/login", json={"username": username, "password": "pw"}).status_code == 200
    return c


def _wait(client, name, seconds=8):
    """Messages received until one called ``name`` arrives."""
    got = []
    end = time.time() + seconds
    while time.time() < end:
        got += client.get_received()
        if any(m["name"] == name for m in got):
            return got
        time.sleep(0.05)
    return got


def test_web_terminal(ssh_server, monkeypatch):
    from config import Config
    from database import RoleModel
    from webserver import app
    from webserver.sockets import socketio
    import socketio as python_socketio
    monkeypatch.setattr(Config, "TERMINAL_ENABLED", True)
    monkeypatch.setattr(Config, "TERMINAL_SSH_HOST", "127.0.0.1")
    monkeypatch.setattr(Config, "TERMINAL_SSH_PORT", ssh_server)
    RoleModel.objects(key="ops").delete()
    RoleModel(key="ops", name="ops", permissions=["terminal"]).save()
    ops = _login("term_ops", role="ops")
    plain = _login("term_plain")

    assert plain.get("/api/terminal/").status_code == 403
    assert ops.get("/api/terminal/").get_json()["port"] == ssh_server

    queue_manager = socketio.server.manager
    socketio.server.manager = python_socketio.Manager()
    socketio.server.manager.set_server(socketio.server)
    try:
        s_plain = socketio.test_client(app, flask_test_client=plain)
        assert s_plain.emit("term_open", {"username": "ops", "password": "right"}, callback=True)["ok"] is False

        s = socketio.test_client(app, flask_test_client=ops)
        # wrong password
        assert s.emit("term_open", {"username": "ops", "password": "wrong"}, callback=True)["ok"] is True
        got = _wait(s, "term_error")
        assert [m["args"][0]["code"] for m in got if m["name"] == "term_error"] == ["auth"]

        # right one: a shell, output relayed, input sent
        s.emit("term_open", {"username": "ops", "password": "right", "cols": 80, "rows": 24}, callback=True)
        got = _wait(s, "term_ready")
        assert any(m["name"] == "term_ready" for m in got)
        out = "".join(m["args"][0]["data"] for m in got if m["name"] == "term_out")
        if "welcome" not in out:
            out += "".join(m["args"][0]["data"] for m in _wait(s, "term_out") if m["name"] == "term_out")
        assert "welcome 歡迎" in out
        s.emit("term_resize", {"cols": 120, "rows": 40})
        # numbered input is written in order even when it arrives out of order
        s.emit("term_in", {"data": "s -l\r", "seq": 1})
        s.emit("term_in", {"data": "l", "seq": 0})
        out = ""
        end = time.time() + 5
        # (the test server echoes each piece it reads: "echo:L" "echo:S -L" or both at once)
        while "LS -L" not in out.replace("echo:", "") and time.time() < end:
            out += "".join(m["args"][0]["data"] for m in s.get_received() if m["name"] == "term_out")
            time.sleep(0.05)
        assert "LS -L" in out.replace("echo:", "")

        # the other end closes: the page hears it
        s.emit("term_in", {"data": "exit\r", "seq": 2})
        got = _wait(s, "term_closed")
        assert any(m["name"] == "term_closed" for m in got)
    finally:
        socketio.server.manager = queue_manager

    from database import ActivityModel
    assert ActivityModel.objects(action="terminal", user="term_ops").count() >= 1


def test_terminal_off_by_default():
    """TERMINAL_ENABLED unset: no permission to give, no page, no session."""
    from config import Config
    from database import RoleModel
    from database.roles import available
    from webserver import app
    from webserver.sockets import socketio
    import socketio as python_socketio
    assert Config.TERMINAL_ENABLED is False
    assert "terminal" not in available() and "train" in available()
    RoleModel.objects(key="ops2").delete()
    RoleModel(key="ops2", name="ops2", permissions=["terminal", "train"]).save()
    ops = _login("term_ops2", role="ops2")
    assert ops.get("/api/terminal/").status_code == 403
    me = ops.get("/api/user/").get_json()
    perms = (me.get("user") or me)["perms"]
    assert "train" in perms and "terminal" not in perms
    queue_manager = socketio.server.manager
    socketio.server.manager = python_socketio.Manager()
    socketio.server.manager.set_server(socketio.server)
    try:
        s = socketio.test_client(app, flask_test_client=ops)
        assert s.emit("term_open", {"username": "x", "password": "y"}, callback=True) == {"ok": False, "code": "disabled"}
    finally:
        socketio.server.manager = queue_manager

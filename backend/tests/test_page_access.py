"""Roles (身分): pages (activity log, models, tasks) and management rights."""
from webserver.util.passwords import hash_password


def _login(username, **fields):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username, **fields).save()
    c = app.test_client()
    c.post("/api/user/login", json={"username": username, "password": "pw"})
    return c


def test_roles_control_pages(world):
    from database import RoleModel, TaskModel, UserModel
    mine = TaskModel(name="mine", group="t", creator="pagesy", completed=True); mine.save()
    other = TaskModel(name="other", group="t", creator="someone", completed=True); other.save()

    c = _login("pagesy", is_admin=False)
    me = c.get("/api/user/").get_json()["user"]
    # the default role: only making categories (everyone could before it was a permission)
    assert me["role"] == "user" and me["perms"] == ["create_categories"]

    assert c.get("/api/activity/").status_code == 403
    assert c.post("/api/activity/1/undo").status_code == 403
    assert c.get("/api/trash/").status_code == 403
    assert c.post("/api/trash/empty").status_code == 403
    assert c.get("/api/model/yolo?all=1").status_code == 403
    assert c.get("/api/admin/roles").status_code == 401

    # without the Tasks page you still see your own tasks (import progress etc.)
    names = {t["name"] for t in c.get("/api/tasks/").get_json()}
    assert "mine" in names and "other" not in names
    assert c.get(f"/api/tasks/{other.id}/logs").status_code == 400
    assert c.get(f"/api/tasks/{mine.id}/logs").status_code == 200

    admin = _login("bossy", is_admin=True)
    roles = admin.get("/api/admin/roles").get_json()
    assert [r["key"] for r in roles["roles"]][:2] == ["admin", "user"]
    r = admin.post("/api/admin/roles", json={"name": "助教", "permissions": ["activity", "tasks", "bogus"]})
    assert r.status_code == 200
    ta = r.get_json()["key"]
    assert admin.post("/api/admin/roles", json={"name": "助教"}).status_code == 400
    assert admin.patch("/api/admin/user/pagesy", json={"role": ta}).get_json()["role"] == ta

    me = c.get("/api/user/").get_json()["user"]
    assert me["role"] == ta and me["perms"] == ["activity", "tasks"]
    assert c.get("/api/activity/").status_code == 200
    assert c.get("/api/trash/").status_code == 200
    assert {"mine", "other"} <= {t["name"] for t in c.get("/api/tasks/").get_json()}
    assert c.get("/api/model/yolo?all=1").status_code == 403

    # the default role can be changed too; the admin role cannot
    assert admin.put("/api/admin/roles/user", json={"permissions": ["tasks"]}).status_code == 200
    assert "tasks" in RoleModel.objects(key="user").first().permissions
    assert admin.put("/api/admin/roles/admin", json={"permissions": []}).status_code == 400
    assert admin.delete("/api/admin/roles/user").status_code == 400
    admin.put("/api/admin/roles/user", json={"permissions": ["create_categories"]})

    # a role is changed by admins only
    assert c.put(f"/api/admin/roles/{ta}", json={"permissions": ["manage_users"]}).status_code == 401

    # removing a role: its users become regular users
    r = admin.delete(f"/api/admin/roles/{ta}")
    assert r.status_code == 200 and r.get_json()["moved"] == 1
    assert c.get("/api/user/").get_json()["user"]["role"] == "user"


def test_manage_users_role(world):
    from database import RoleModel, UserModel
    RoleModel(key="hr", name="HR", permissions=["manage_users"]).save()
    try:
        c = _login("hrperson", role="hr")
        _login("adminy", is_admin=True)
        _login("plain")
        assert c.get("/api/admin/users").status_code == 200
        assert c.post("/api/admin/user/", json={"username": "newbie", "password": "pw", "name": "N"}).status_code == 200
        assert c.patch("/api/admin/user/newbie", json={"name": "Newbie"}).status_code == 200
        # cannot make admins, touch admins or change their own role
        assert c.patch("/api/admin/user/newbie", json={"role": "admin"}).status_code == 403
        assert c.patch("/api/admin/user/newbie", json={"isAdmin": True}).status_code == 403
        assert c.patch("/api/admin/user/adminy", json={"name": "x"}).status_code == 403
        assert c.delete("/api/admin/user/adminy").status_code == 403
        assert c.patch("/api/admin/user/hrperson", json={"role": "user"}).status_code == 400
        assert c.delete("/api/admin/user/plain").status_code == 200
        assert not UserModel.objects(username="newbie").first().is_admin
    finally:
        RoleModel.objects(key="hr").delete()


def test_all_datasets_role(world):
    from database import RoleModel
    RoleModel(key="viewall", name="All", permissions=["all_datasets"]).save()
    try:
        plain = _login("nobody")
        seer = _login("seer", role="viewall")
        assert plain.get("/api/dataset/data").get_json()["total"] == 0
        assert seer.get("/api/dataset/data").get_json()["total"] >= 1
    finally:
        RoleModel.objects(key="viewall").delete()


def test_admin_has_everything(world):
    c = _login("bossy2", is_admin=True)
    me = c.get("/api/user/").get_json()["user"]
    assert me["role"] == "admin" and "manage_users" in me["perms"]
    assert c.get("/api/activity/").status_code == 200


def test_task_list_details_and_clear(world):
    from database import TaskModel
    c = _login("taskboss", is_admin=True)
    ds = c.post("/api/dataset/", json={"name": "taskds"}).get_json()["id"]
    done = TaskModel(name="done", group="Scanner", creator="taskboss", dataset_id=ds); done.save()
    done.set_progress(100)
    running = TaskModel(name="running", group="Scanner", creator="taskboss"); running.save()
    tasks = {t["name"]: t for t in c.get("/api/tasks/").get_json()}
    assert tasks["done"]["dataset_name"] == "taskds" and tasks["done"]["start_date"] and tasks["done"]["end_date"]
    assert c.delete("/api/tasks/completed").get_json()["deleted"] >= 1
    names = {t["name"] for t in c.get("/api/tasks/").get_json()}
    assert "done" not in names and "running" in names

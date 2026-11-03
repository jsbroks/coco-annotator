"""Training runs: permission, queue, the runner with a stand-in for Ultralytics."""
import os
import sys
import threading
import time

from webserver.util.passwords import hash_password

FAKE = r'''
import csv, os, sys, time
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
if "resume" in args:  # go on: runs/train/weights/last.pt
    out = os.path.dirname(os.path.dirname(args["resume"]))
    epochs = int(open(os.path.join(out, "epochs.txt")).read())
    done = len(open(os.path.join(out, "results.csv")).read().splitlines()) - 1
    mode = "a"
    print(f"Resuming from epoch {done + 1}", flush=True)
else:
    out = os.path.join(args["project"], args["name"])
    os.makedirs(os.path.join(out, "weights"), exist_ok=True)
    epochs = int(args["epochs"])
    assert os.path.exists(args["data"]), args["data"]
    open(os.path.join(out, "epochs.txt"), "w").write(str(epochs))
    done, mode = 0, "w"
with open(os.path.join(out, "results.csv"), mode, newline="") as fp:
    w = csv.writer(fp)
    if mode == "w":
        w.writerow(["                  epoch", "      train/box_loss", "   metrics/mAP50(B)", " metrics/mAP50-95(B)"])
    for e in range(done + 1, epochs + 1):
        w.writerow([e, 1.0 / e, 0.1 * e, 0.3 if e == 2 else 0.1]); fp.flush()
        open(os.path.join(out, "weights", "last.pt"), "wb").write(b"last")
        print(f"\x1b[K\x1b[1mepoch {e}/{epochs}\x1b[0m", flush=True)
        time.sleep(float(os.environ.get("FAKE_EPOCH_SECONDS", "0")))
open(os.path.join(out, "weights", "best.pt"), "wb").write(b"weights")
'''


CATALOG = {
    "version": "8.4.0",
    "families": [{"key": "yolo26", "label": "YOLO26", "items": [
        {"name": n, "kind": n.rsplit(".", 1)[1], "task": "segment" if "-seg" in n else "detect", "scale": n[6]}
        for n in ("yolo26n.pt", "yolo26s.pt", "yolo26s.yaml", "yolo26s-seg.pt")]}],
    "args": {"epochs": 100, "batch": 16, "lr0": 0.01, "mosaic": 1.0, "freeze": None, "pretrained": True,
             "optimizer": "auto", "cos_lr": False, "device": None},
}


def _login(username, role=None):
    from database import UserModel
    from webserver import app
    UserModel.objects(username=username).delete()
    UserModel(username=username, password=hash_password("pw"), name=username, is_admin=False,
              role=role or "user").save()
    c = app.test_client()
    assert c.post("/api/user/login", json={"username": username, "password": "pw"}).status_code == 200
    return c


def _fake_command(script):
    def build(run, data, out_dir):
        p = run.params
        if p.get("resume"):
            from trainer import runner
            return [sys.executable, script, f"resume={runner.last_weights(run.id)}"]
        return [sys.executable, script, f"data={data}", f"epochs={p['epochs']}", f"project={out_dir}", "name=train"]
    return build


def test_training(dataset_directory, tmp_path, monkeypatch):
    from PIL import Image
    from database import RoleModel, TrainRunModel
    from trainer import runner
    from config import Config
    models = tmp_path / "models"
    models.mkdir()
    monkeypatch.setenv("MODELS_DIRECTORY", str(models))
    monkeypatch.setattr(Config, "MODELS_DIRECTORY", str(models))
    monkeypatch.setattr(runner, "POLL_SECONDS", 0.1)
    RoleModel.objects(key="trainer").delete()
    RoleModel(key="trainer", name="trainer", permissions=["train"]).save()
    script = tmp_path / "fake_yolo.py"
    script.write_text(FAKE)

    t = _login("tr_owner", role="trainer")
    plain = _login("tr_plain")
    ds = t.post("/api/dataset/", json={"name": "tr_ds", "categories": ["boat"]}).get_json()["id"]
    folder = os.path.join(dataset_directory, "tr_ds")
    os.makedirs(folder, exist_ok=True)
    Image.new("RGB", (64, 48)).save(os.path.join(folder, "a.jpg"))
    t.get(f"/api/dataset/{ds}/scan")
    image = t.get(f"/api/dataset/{ds}/data").get_json()["images"][0]
    cat = t.get(f"/api/dataset/{ds}/data").get_json()["dataset"]["categories"][0]
    t.post("/api/annotation/", json={"image_id": image["id"], "category_id": cat,
                                    "segmentation": [[5, 5, 30, 5, 30, 30, 5, 30]]})
    # an export without images can not be trained on; one with images can
    t.get(f"/api/dataset/{ds}/export", query_string={"format": "yolo", "yolo_task": "detect"})
    t.get(f"/api/dataset/{ds}/export", query_string={"format": "yolo", "yolo_task": "detect", "with_images": "true"})

    assert plain.get("/api/train/").status_code == 403
    exports = t.get("/api/train/exports").get_json()["exports"]
    mine = [e for e in exports if e["dataset_id"] == ds]
    assert len(mine) == 1 and mine[0]["task"] == "detect" and mine[0]["datasets"] == ["tr_ds"]
    eid = mine[0]["id"]

    # what the trainer can train (it publishes this when it starts)
    runner.heartbeat("CPU", CATALOG)
    assert t.post("/api/train/", json={"export_id": eid, "family": "nope"}).status_code == 400
    r = t.post("/api/train/", json={"export_id": eid, "family": "yolo26", "size": "s", "epochs": 3, "imgsz": 650})
    assert r.status_code == 200, r.data
    run = r.get_json()
    assert run["status"] == "queued" and run["params"]["model"] == "yolo26s.pt" and run["params"]["imgsz"] == 640
    assert t.get("/api/train/").get_json()["runs"][0]["queue_position"] == 1
    assert plain.post("/api/train/", json={"export_id": eid}).status_code == 403

    # the trainer picks it up and runs it
    claimed = runner.claim_next()
    assert claimed.id == run["id"] and runner.claim_next() is None
    runner.execute(claimed, command=_fake_command(str(script)))
    done = t.get(f"/api/train/{run['id']}").get_json()
    assert done["status"] == "done", done
    assert done["epoch"] == 3 and done["metrics"][-1]["metrics/mAP50(B)"] == 0.3
    # best.pt is from epoch 2 (Ultralytics' fitness: 0.1 mAP50 + 0.9 mAP50-95 here)
    assert done["best"]["epoch"] == 2 and done["best"]["since"] == 1
    assert done["best"]["metrics"]["metrics/mAP50-95(B)"] == 0.3
    assert [r["best"]["epoch"] for r in t.get("/api/train/").get_json()["runs"] if r["id"] == run["id"]] == [2]
    assert done["model_name"] == f"trained/tr_ds-detect-run{run['id']}.pt"
    assert (models / done["model_name"]).read_bytes() == b"weights"
    # everything under runs/train, packed when it ended
    import io
    import zipfile
    assert done["archive"]["size"] > 0
    got = t.get(f"/api/train/{run['id']}/download")
    assert got.status_code == 200 and "tr_ds-detect-run" in got.headers["Content-Disposition"]
    names = zipfile.ZipFile(io.BytesIO(got.data)).namelist()
    top = f"tr_ds-detect-run{run['id']}/"
    assert {top + "weights/best.pt", top + "results.csv", top + "train.log"} <= set(names)
    assert plain.get(f"/api/train/{run['id']}/download").status_code == 403
    # runs from before: packed when downloaded
    os.remove(runner.archive_path(run["id"]))
    assert t.get(f"/api/train/{run['id']}").get_json()["archive"] == {"size": None}
    assert t.get(f"/api/train/{run['id']}/download").status_code == 200
    assert "epoch 3/3" in done["log_tail"] and "\x1b" not in done["log_tail"]  # no terminal colour codes

    # stopping a running one
    monkeypatch.setenv("FAKE_EPOCH_SECONDS", "0.5")
    r2 = t.post("/api/train/", json={"export_id": eid, "epochs": 50}).get_json()
    claimed = runner.claim_next()
    worker = threading.Thread(target=runner.execute, args=(claimed,), kwargs={"command": _fake_command(str(script))})
    worker.start()
    time.sleep(1.5)
    assert t.post(f"/api/train/{r2['id']}/stop").get_json()["stop_requested"] is True
    worker.join(timeout=20)
    stopped = TrainRunModel.objects(id=r2["id"]).first()
    assert stopped.status == "stopped" and 0 < stopped.epoch < 50

    # removing a running one: stopped, then gone (no model kept)
    monkeypatch.setenv("FAKE_EPOCH_SECONDS", "0.3")
    r4 = t.post("/api/train/", json={"export_id": eid, "epochs": 50}).get_json()
    claimed = runner.claim_next()
    worker = threading.Thread(target=runner.execute, args=(claimed,), kwargs={"command": _fake_command(str(script))})
    worker.start()
    time.sleep(1)
    assert _login("tr_other3", role="trainer").delete(f"/api/train/{r4['id']}").status_code == 403
    assert t.delete(f"/api/train/{r4['id']}").get_json() == {"success": True, "deleting": True}
    worker.join(timeout=20)
    assert TrainRunModel.objects(id=r4["id"]).first() is None
    assert not os.path.exists(runner.work_dir(r4["id"]))
    assert not (models / f"trained/tr_ds-detect-run{r4['id']}.pt").exists()
    # a queued one goes at once
    r5 = t.post("/api/train/", json={"export_id": eid}).get_json()
    assert t.delete(f"/api/train/{r5['id']}").get_json() == {"success": True}
    assert TrainRunModel.objects(id=r5["id"]).first() is None
    monkeypatch.setenv("FAKE_EPOCH_SECONDS", "0")

    # a queued one is simply cancelled; finished ones can be removed
    assert t.get(f"/api/train/{r2['id']}").get_json()["archive"]["size"] > 0  # a stopped one too

    # go on from where it stopped
    monkeypatch.setenv("FAKE_EPOCH_SECONDS", "0")
    assert t.get(f"/api/train/{r2['id']}").get_json()["resumable"] is True
    assert plain.post(f"/api/train/{r2['id']}/resume").status_code == 403
    assert _login("tr_other2", role="trainer").post(f"/api/train/{r2['id']}/resume").status_code == 403
    steps = os.path.join(runner.work_dir(r2["id"]), "steps.jsonl")
    stopped_at = TrainRunModel.objects(id=r2["id"]).first().epoch
    with open(steps, "w") as fp:
        fp.write('{"x": 0.5}\n{"x": %d}\n{"x": %d.5}\n' % (stopped_at, stopped_at))
    resumed = t.post(f"/api/train/{r2['id']}/resume").get_json()
    assert resumed["status"] == "queued" and resumed["params"]["resume"] and resumed["params"]["resumes"] == 1
    claimed = runner.claim_next()
    assert claimed.id == r2["id"]
    runner.execute(claimed, command=_fake_command(str(script)))
    again = t.get(f"/api/train/{r2['id']}").get_json()
    assert again["status"] == "done", again
    assert [m["epoch"] for m in again["metrics"]] == list(range(1, 51))  # no epoch twice, none missing
    assert "resumed after epoch" in again["log_tail"] and again["resumable"] is False
    assert open(steps).read() == '{"x": 0.5}\n{"x": %d}\n' % stopped_at  # the cut-off epoch's points go
    assert t.post(f"/api/train/{r2['id']}/resume").status_code == 400  # finished: nothing to resume
    assert t.post(f"/api/train/{run['id']}/resume").status_code == 400

    # the trainer stopped in the middle (server restarted): queued again, to go on
    from database import TrainRunModel as Runs
    Runs.objects(id=r2["id"]).update_one(set__status="running", set__epoch=10)
    no_weights = Runs(name="x", creator="tr_owner", export_id=eid, dataset_id=ds, task="detect",
                      status="running", epochs=5)
    no_weights.save()
    runner.recover()
    assert Runs.objects(id=r2["id"]).first().status == "queued"
    assert Runs.objects(id=r2["id"]).first().params["resumes"] == 2
    assert Runs.objects(id=no_weights.id).first().status == "failed"
    Runs.objects(id=r2["id"]).update_one(set__status="done")
    r3 = t.post("/api/train/", json={"export_id": eid}).get_json()
    assert t.get(f"/api/train/{r3['id']}/download").status_code == 400  # not finished
    assert t.post(f"/api/train/{r3['id']}/stop").get_json()["status"] == "stopped"
    assert t.delete(f"/api/train/{run['id']}").get_json()["success"]
    assert (models / done["model_name"]).exists()  # the trained model stays

    st = t.get("/api/train/status").get_json()
    assert "alive" in st and st["tasks"][0] == "detect"
    assert st["version"] == "8.4.0"

    # the catalog: official models (.pt / .yaml) and the arguments
    cat = t.get("/api/train/catalog").get_json()
    assert [i["name"] for i in cat["families"][0]["items"]][:2] == ["yolo26n.pt", "yolo26s.pt"]
    assert cat["args"]["lr0"] == 0.01 and "data" in cat["blocked"]
    assert plain.get("/api/train/catalog").status_code == 403

    def queue(**body):
        return t.post("/api/train/", json={"export_id": eid, **body})

    # a .yaml from scratch, with own arguments (epochs among them)
    r = queue(model="yolo26s.yaml", extra={"lr0": 0.002, "cos_lr": True, "freeze": [0, 1], "epochs": 7,
                                           "optimizer": "AdamW", "pretrained": "yolo26n.pt", "batch": 0.7})
    assert r.status_code == 200, r.data
    p = r.get_json()["params"]
    assert p["model"] == "yolo26s.yaml" and p["epochs"] == 7 and p["batch"] == 0.7
    assert "export_augment" in p and p["export_augment"] is None  # the export was not augmented
    assert "export_augment" in t.get(f"/api/train/{r.get_json()['id']}").get_json()["params"]
    assert p["extra"] == {"lr0": 0.002, "cos_lr": True, "freeze": [0, 1], "optimizer": "AdamW",
                          "pretrained": "yolo26n.pt"}
    cmd = runner.build_command(TrainRunModel.objects(id=r.get_json()["id"]).first(), "/d/data.yaml", "/out")
    assert "model=yolo26s.yaml" in cmd and "lr0=0.002" in cmd and "cos_lr=True" in cmd and "freeze=[0, 1]" in cmd
    assert f"pretrained={models}/.training/base/yolo26n.pt" in cmd
    assert cmd[-3:] == ["project=/out", "name=train", "exist_ok=True"]  # nothing overrides where it goes
    t.post(f"/api/train/{r.get_json()['id']}/stop")

    for bad in ({"model": "yolo26s-seg.pt"},                 # another task
                {"model": "yolo99.pt"},                      # not in the catalog
                {"model": "yolo26n.pt", "extra": {"data": "x"}},        # set by the trainer
                {"model": "yolo26n.pt", "extra": {"project": "x"}},
                {"model": "yolo26n.pt", "extra": {"nonsense": 1}},      # unknown
                {"model": "yolo26n.pt", "extra": {"optimizer": "../../etc"}},  # paths
                {"model": "yolo26n.pt", "extra": {"optimizer": "a\nb"}},
                {"model": "yolo26n.pt", "extra": {"pretrained": "yolo26s.pt"}},  # a .pt has its weights
                {"model": "yolo26s.yaml", "extra": {"pretrained": "yolo26s.yaml"}},
                {"source": "upload", "upload_id": 999}):
        assert queue(**bad).status_code == 400, bad

    # uploads: a model yaml, weights; anything else is refused
    import io
    arch = b"nc: 80\nscales:\n  s: [0.5, 0.5, 1024]\nbackbone: []\nhead: []\n"
    up = t.post("/api/train/uploads", data={"file": (io.BytesIO(arch), "my-yolo26s.yaml")},
                content_type="multipart/form-data")
    assert up.status_code == 200, up.data
    up = up.get_json()
    assert up["kind"] == "yaml" and up["name"] == "my-yolo26s.yaml"
    # loading a .pt runs code from it: "train" alone may not upload one
    assert t.post("/api/train/uploads", data={"file": (io.BytesIO(b"PK\x03\x04weights"), "best.pt")},
                  content_type="multipart/form-data").status_code == 403
    from database import UserModel
    UserModel.objects(username="tr_owner").update(set__is_admin=True)
    w = t.post("/api/train/uploads", data={"file": (io.BytesIO(b"PK\x03\x04weights"), "best.pt")},
               content_type="multipart/form-data").get_json()
    assert w["kind"] == "pt"
    for name, body in (("x.txt", b"hi"), ("x.yaml", b"lr0: 1\n"), ("x.pt", b"not torch")):
        assert t.post("/api/train/uploads", data={"file": (io.BytesIO(body), name)},
                      content_type="multipart/form-data").status_code == 400, name
    UserModel.objects(username="tr_owner").update(set__is_admin=False)
    assert [u["id"] for u in t.get("/api/train/uploads").get_json()["uploads"]] == [w["id"], up["id"]]
    assert len(os.listdir(models / ".training" / "uploads")) == 2

    r = queue(source="upload", upload_id=up["id"], extra={"pretrained": f"upload:{w['id']}"})
    assert r.status_code == 200, r.data
    p = r.get_json()["params"]
    assert p["model"].endswith(f"u{up['id']}-my-yolo26s.yaml") and p["label"] == "my-yolo26s.yaml"
    assert p["extra"]["pretrained"].endswith(f"best-u{w['id']}.pt")
    cmd = runner.build_command(TrainRunModel.objects(id=r.get_json()["id"]).first(), "/d", "/o")
    assert f"pretrained={p['extra']['pretrained']}" in cmd
    t.post(f"/api/train/{r.get_json()['id']}/stop")

    other = _login("tr_other", role="trainer")
    assert other.delete(f"/api/train/uploads/{w['id']}").status_code == 403
    assert t.delete(f"/api/train/uploads/{w['id']}").get_json()["success"]
    assert len(os.listdir(models / ".training" / "uploads")) == 1

    # an args.yaml (e.g. of an earlier run): what can be used, what not
    args_yaml = (b"task: detect\nmodel: /x/yolo26n.pt\ndata: d.yaml\nepochs: 30\nlr0: 0.005\n"
                 b"mosaic: 1.0\nbogus: 3\noptimizer: SGD\n")
    parsed = t.post("/api/train/parse-args", data={"file": (io.BytesIO(args_yaml), "args.yaml")},
                    content_type="multipart/form-data").get_json()
    assert parsed["args"] == {"epochs": 30, "lr0": 0.005, "optimizer": "SGD"}  # mosaic is the default
    assert sorted(i["key"] for i in parsed["ignored"]) == ["bogus", "data", "model", "task"]
    assert t.post("/api/train/parse-args", data={"file": (io.BytesIO(b"- a\n- b\n"), "a.yaml")},
                  content_type="multipart/form-data").status_code == 400


def test_log_follower(tmp_path):
    """Progress bars (\\r ten times a second) keep only their last state."""
    from trainer.runner import LogFollower
    path = tmp_path / "train.log"
    with open(path, "wb") as fp:
        out = LogFollower(fp)
        out.feed("Ultralytics 8.4 \x1b[1mCPU\x1b[0m\r\nepoch 1/2\n".encode())
        for i in range(1, 2001):
            out.feed(f"\r\x1b[K  1/2  {i}/2000 \u2501\u2501 loss {1 / i:.3f}".encode())
            if i == 1000:
                tail = out.tail()
                assert tail.splitlines()[:2] == ["Ultralytics 8.4 CPU", "epoch 1/2"]
                assert tail.splitlines()[-1].strip().startswith("1/2  1000/2000")
        # a character cut in two between reads
        data = "\n驗證完成\n".encode()
        out.feed(data[:3])
        out.feed(data[3:])
        out.feed(b"")
    lines = path.read_text().splitlines()
    assert lines == ["Ultralytics 8.4 CPU", "epoch 1/2", "  1/2  2000/2000 \u2501\u2501 loss 0.001", "驗證完成"]
    assert path.stat().st_size < 200
    assert "\r" not in out.tail() and "\x1b" not in out.tail()


def test_live_output(tmp_path, monkeypatch):
    """The page watching a run gets its new lines and progress bar as written."""
    from database import RoleModel, TrainRunModel
    from webserver import app
    from webserver.sockets import socketio
    from webserver import train_live
    from trainer import runner
    monkeypatch.setenv("MODELS_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(train_live, "STATUS_SECONDS", 0.2)
    RoleModel.objects(key="trainer").delete()
    RoleModel(key="trainer", name="trainer", permissions=["train"]).save()
    run = TrainRunModel(name="live", creator="tr_live", export_id=1, dataset_id=1, task="detect", status="running")
    run.save()
    work = runner.work_dir(run.id)
    os.makedirs(work)
    log = open(os.path.join(work, "train.log"), "ab")
    log.write(b"$ yolo train\nUltralytics 8.4\n")
    log.flush()
    out = runner.LogFollower(log, os.path.join(work, "progress.txt"))

    import socketio as python_socketio
    queue_manager = socketio.server.manager
    socketio.server.manager = python_socketio.Manager()
    socketio.server.manager.set_server(socketio.server)
    try:
        s_plain = socketio.test_client(app, flask_test_client=_login("tr_live_plain"))
        assert s_plain.emit("train_watch", {"run_id": run.id}, callback=True)["ok"] is False
        s = socketio.test_client(app, flask_test_client=_login("tr_live", role="trainer"))
        first = s.emit("train_watch", {"run_id": run.id}, callback=True)
        assert first["ok"] and first["lines"] == ["$ yolo train", "Ultralytics 8.4"] and first["live"]

        def received(until, seconds=5):
            got, end = [], time.time() + seconds
            while time.time() < end:
                got += [m["args"][0] for m in s.get_received() if m["name"] == "train_log"]
                if until(got):
                    break
                time.sleep(0.05)
            return got

        out.feed(b"epoch 1/2\n\r\x1b[K 1/2 3/10 \xe2\x94\x81")
        got = received(lambda g: any(e["progress"] == "1/2 3/10 ━".rjust(len(e["progress"])) for e in g))
        assert ["epoch 1/2"] == [l for e in got for l in e["lines"]]
        assert got[-1]["progress"].strip() == "1/2 3/10 ━"
        t0 = time.time()
        out.feed(b"\r\x1b[K 1/2 4/10")
        got = received(lambda g: any(e["progress"].strip() == "1/2 4/10" for e in g))
        assert got and time.time() - t0 < 1  # live, not once a second
        # a second page shares the watcher, without lines twice
        # another trainer who may not see the run's dataset gets nothing
        s_other = socketio.test_client(app, flask_test_client=_login("tr_live_other", role="trainer"))
        assert s_other.emit("train_watch", {"run_id": run.id}, callback=True)["ok"] is False
        s_other.disconnect()
        c2 = _login("tr_live2", role="trainer")
        from database import UserModel
        UserModel.objects(username="tr_live2").update(set__is_admin=True)
        s2 = socketio.test_client(app, flask_test_client=c2)
        assert s2.emit("train_watch", {"run_id": run.id}, callback=True)["lines"][-1] == "epoch 1/2"
        out.feed(b"\ndone\n")
        got = received(lambda g: any("done" in e["lines"] for e in g))
        assert [l for e in got for l in e["lines"]] == ["1/2 4/10", "done"] or \
            [l.strip() for e in got for l in e["lines"]] == ["1/2 4/10", "done"]
        assert [m["args"][0]["lines"] for m in s2.get_received() if m["name"] == "train_log" and m["args"][0]["lines"]] \
            == [[" 1/2 4/10", "done"]]
        # finished: the watcher stops
        run.update(set__status="done")
        time.sleep(1)
        assert run.id not in train_live.WATCHERS
    finally:
        socketio.server.manager = queue_manager
    log.close()


def test_steps(tmp_path, monkeypatch):
    """Points within each epoch, from the progress bar: kept by the trainer,
    given by the API (thinned out), pushed live."""
    import json
    from database import RoleModel, TrainRunModel
    from trainer import runner
    monkeypatch.setenv("MODELS_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(runner, "STEP_SECONDS", 0)
    RoleModel.objects(key="trainer").delete()
    RoleModel(key="trainer", name="trainer", permissions=["train"]).save()
    run = TrainRunModel(name="steps", creator="tr_steps", export_id=1, dataset_id=1, task="detect", status="running")
    run.save()
    work = runner.work_dir(run.id)
    os.makedirs(work)
    steps = os.path.join(work, "steps.jsonl")
    with open(os.path.join(work, "train.log"), "ab") as log:
        out = runner.LogFollower(log, os.path.join(work, "progress.txt"), steps)
        out.feed(b"      Epoch    GPU_mem   box_loss   cls_loss   dfl_loss  Instances       Size\n")
        for e in (1, 2):
            for b in range(1, 11):
                bar = f"\r\x1b[K{e:>11}/2      1.5G      {2 / (e * b):.3f}      0.900      1.100         12        640: {b * 10}% ━━ {b}/10 3it/s"
                out.feed(bar.encode())
            out.feed(b"\n")
            out.feed("                 Class     Images  Instances      Box(P          R      mAP50  mAP50-95): 100% ━━ 1/1\n".encode())
    points = [json.loads(l) for l in open(steps)]
    assert len(points) == 20 and points[0] == {"box_loss": 2.0, "cls_loss": 0.9, "dfl_loss": 1.1, "x": 0.1, "gpu_mem": 1.5}
    assert points[9]["x"] == 1.0 and points[-1]["x"] == 2.0 and points[-1]["box_loss"] == 0.1

    t = _login("tr_steps", role="trainer")
    got = t.get(f"/api/train/{run.id}/steps").get_json()
    assert got["total"] == 20 and got["points"] == points
    from webserver.api import train as train_api
    monkeypatch.setattr(train_api, "MAX_STEPS", 4)
    thin = t.get(f"/api/train/{run.id}/steps").get_json()["points"]
    assert len(thin) < 20 and {1.0, 2.0} <= {p["x"] for p in thin}  # epoch ends kept
    assert _login("tr_steps_plain").get(f"/api/train/{run.id}/steps").status_code == 403


class _TestSite:
    """trainer.worker.Site over the Flask test client."""

    def __init__(self, client, token):
        self.c = client
        self.h = {"X-Worker-Token": token}

    def post(self, path, json_body=None, timeout=30, data=None, files=None):
        if isinstance(data, bytes):
            r = self.c.post(f"/api/worker/{path}", data=data, headers=self.h)
        elif files is not None or data is not None:
            form = dict(data or {})
            for key, (name, fp) in (files or {}).items():
                form[key] = (fp, name)
            r = self.c.post(f"/api/worker/{path}", data=form, headers=self.h, content_type="multipart/form-data")
        else:
            r = self.c.post(f"/api/worker/{path}", json=json_body, headers=self.h)
        if r.status_code == 401:
            raise PermissionError("token")
        assert r.status_code < 400, (path, r.status_code, r.data)
        return r.get_json() if r.status_code != 204 and r.data else None

    def download(self, path, dest, progress=None):
        r = self.c.get(f"/api/worker/{path}", headers=self.h)
        if r.status_code == 404:
            raise ValueError("not found")
        with open(dest, "wb") as fp:
            fp.write(r.data)
        if progress and progress(len(r.data), len(r.data)):
            from trainer.worker import Stopped
            raise Stopped()
        return dest


def test_other_servers(dataset_directory, tmp_path, monkeypatch):
    """Another server trains (a worker over the web API): targeted or any."""
    import io
    import zipfile
    from types import SimpleNamespace
    from PIL import Image
    from database import RoleModel, TrainRunModel, UserModel
    from trainer import runner, worker
    from webserver import app
    from webserver.api import train_worker, train as train_api
    from config import Config

    site_dir, worker_dir = tmp_path / "site", tmp_path / "worker"
    site_dir.mkdir()
    worker_dir.mkdir()
    # the site's files and the worker's are on different servers
    monkeypatch.setenv("MODELS_DIRECTORY", str(worker_dir))
    monkeypatch.setattr(Config, "MODELS_DIRECTORY", str(site_dir))
    site_work = lambda i: os.path.join(str(site_dir), ".training", f"run-{i}")  # noqa: E731
    for mod in (train_worker, train_api):
        monkeypatch.setattr(mod, "work_dir", site_work)
    monkeypatch.setattr(train_worker, "models_dir", lambda: str(site_dir))
    monkeypatch.setattr(train_worker, "archive_path", lambda i: os.path.join(site_work(i), "results.zip"))
    monkeypatch.setattr(train_api, "uploads_dir", lambda: os.path.join(str(site_dir), ".training", "uploads"))
    monkeypatch.setattr(runner, "POLL_SECONDS", 0.1)
    monkeypatch.setattr(worker, "POLL_SECONDS", 0.1)
    TrainRunModel.objects(status__in=["queued", "running"]).update(set__status="stopped")
    RoleModel.objects(key="trainer").delete()
    RoleModel(key="trainer", name="trainer", permissions=["train"]).save()
    script = tmp_path / "fake_yolo.py"
    script.write_text(FAKE)

    UserModel.objects(username="tr_admin").delete()
    UserModel(username="tr_admin", password=hash_password("pw"), name="a", is_admin=True).save()
    admin = app.test_client()
    admin.post("/api/user/login", json={"username": "tr_admin", "password": "pw"})
    t = _login("tr_remote", role="trainer")

    # an export to train on
    ds = t.post("/api/dataset/", json={"name": "tr_remote_ds", "categories": ["boat"]}).get_json()["id"]
    folder = os.path.join(dataset_directory, "tr_remote_ds")
    os.makedirs(folder, exist_ok=True)
    Image.new("RGB", (64, 48)).save(os.path.join(folder, "a.jpg"))
    t.get(f"/api/dataset/{ds}/scan")
    data = t.get(f"/api/dataset/{ds}/data").get_json()
    t.post("/api/annotation/", json={"image_id": data["images"][0]["id"], "category_id": data["dataset"]["categories"][0],
                                    "segmentation": [[5, 5, 30, 5, 30, 30, 5, 30]]})
    t.get(f"/api/dataset/{ds}/export", query_string={"format": "yolo", "yolo_task": "detect", "with_images": "true"})
    eid = [e for e in t.get("/api/train/exports").get_json()["exports"] if e["dataset_id"] == ds][0]["id"]
    runner.heartbeat("CPU", CATALOG, name="main")

    # admins add a server: its token, once
    assert t.post("/api/worker/servers", json={"name": "gpu2"}).status_code == 403
    assert admin.post("/api/worker/servers", json={"name": "bad name!"}).status_code == 400
    token = admin.post("/api/worker/servers", json={"name": "gpu2"}).get_json()["token"]
    assert admin.post("/api/worker/servers", json={"name": "gpu2"}).status_code == 400
    assert admin.post("/api/worker/servers", json={"name": "main"}).status_code == 400  # this server's trainer
    names = {x["name"]: x for x in t.get("/api/train/status").get_json()["trainers"]}
    assert names["gpu2"]["alive"] is False and names["main"]["alive"] is True
    assert app.test_client().post("/api/worker/claim", headers={"X-Worker-Token": "nope"}).status_code == 401

    # a training for gpu2, one for any trainer, one for an unknown one
    assert t.post("/api/train/", json={"export_id": eid, "target": "nope"}).status_code == 400
    upload = admin.post("/api/train/uploads", data={"file": (io.BytesIO(b"PK\x03\x04w"), "mine.pt")},
                        content_type="multipart/form-data").get_json()
    mine = t.post("/api/train/", json={"export_id": eid, "epochs": 3, "target": "gpu2", "source": "upload",
                                      "upload_id": upload["id"]}).get_json()
    anyone = t.post("/api/train/", json={"export_id": eid, "epochs": 2}).get_json()
    assert mine["target"] == "gpu2" and anyone["target"] == ""
    # this server's trainer skips the one meant for gpu2
    took = runner.claim_next("main")
    assert took.id == anyone["id"] and took.worker == "main"
    TrainRunModel.objects(id=anyone["id"]).update_one(set__status="stopped")

    site = _TestSite(app.test_client(), token)
    site.post("hello", {"device": "RTX 3090", "catalog": CATALOG, "resumable": []})
    names = {x["name"]: x for x in t.get("/api/train/status").get_json()["trainers"]}
    assert names["gpu2"]["alive"] and names["gpu2"]["device"] == "RTX 3090" and names["gpu2"]["kind"] == "remote"

    job = site.post("claim")
    assert job["id"] == mine["id"] and job["files"] == [{"field": "model", "index": 0, "name": "mine-u%d.pt" % upload["id"],
                                                        "size": 5}]
    run = SimpleNamespace(id=job["id"], task=job["task"], params=dict(job["params"]), epoch=0,
                          epochs=job["epochs"], dataset_names=job["dataset_names"])
    remote = worker.RemoteIO(site, job, run)
    worker.execute(run, command=_fake_command(str(script)), io=remote)
    # the model file came from the site, into the worker's folder
    assert run.params["model"] == os.path.join(str(worker_dir), ".cache", "files", job["files"][0]["name"])
    done = t.get(f"/api/train/{mine['id']}").get_json()
    assert done["status"] == "done" and done["worker"] == "gpu2" and done["epoch"] == 3, done
    assert done["model_name"] == f"trained/tr_remote_ds-detect-run{mine['id']}.pt"
    assert (site_dir / done["model_name"]).read_bytes() == b"weights"
    names_in_zip = zipfile.ZipFile(os.path.join(site_work(mine["id"]), "results.zip")).namelist()
    assert any(n.endswith("weights/best.pt") for n in names_in_zip)
    site_log = open(os.path.join(site_work(mine["id"]), "train.log")).read()
    assert "epoch 3/3" in site_log and "\x1b" not in site_log
    assert not os.path.exists(runner.work_dir(mine["id"]))  # finished: nothing kept on the worker

    # stopped on the worker: it keeps its last epoch, and resumes there
    monkeypatch.setenv("FAKE_EPOCH_SECONDS", "0.3")
    slow = t.post("/api/train/", json={"export_id": eid, "epochs": 40, "target": "gpu2"}).get_json()
    job = site.post("claim")
    run = SimpleNamespace(id=job["id"], task=job["task"], params=dict(job["params"]), epoch=0,
                          epochs=job["epochs"], dataset_names=job["dataset_names"])
    import threading
    th = threading.Thread(target=worker.execute, args=(run,),
                          kwargs={"command": _fake_command(str(script)), "io": worker.RemoteIO(site, job, run)})
    th.start()
    time.sleep(1.5)
    t.post(f"/api/train/{slow['id']}/stop")
    th.join(timeout=30)
    stopped = t.get(f"/api/train/{slow['id']}").get_json()
    assert stopped["status"] == "stopped" and 0 < stopped["epoch"] < 40 and stopped["resumable"], stopped
    assert os.path.isfile(runner.last_weights(slow["id"]))  # kept on the worker
    monkeypatch.setenv("FAKE_EPOCH_SECONDS", "0")
    resumed = t.post(f"/api/train/{slow['id']}/resume").get_json()
    assert resumed["target"] == "gpu2"  # only gpu2 has its weights
    assert runner.claim_next("main") is None
    job = site.post("claim")
    assert job["id"] == slow["id"] and job["params"]["resume"]
    run = SimpleNamespace(id=job["id"], task=job["task"], params=dict(job["params"]), epoch=job["epoch"],
                          epochs=job["epochs"], dataset_names=job["dataset_names"])
    worker.execute(run, command=_fake_command(str(script)), io=worker.RemoteIO(site, job, run))
    again = t.get(f"/api/train/{slow['id']}").get_json()
    assert again["status"] == "done" and [m["epoch"] for m in again["metrics"]] == list(range(1, 41))

    # the worker restarted in the middle of one: queued to resume where it has the weights
    TrainRunModel.objects(id=slow["id"]).update_one(set__status="running", set__epoch=10, set__worker="gpu2")
    os.makedirs(os.path.dirname(runner.last_weights(slow["id"])), exist_ok=True)
    open(runner.last_weights(slow["id"]), "wb").write(b"last")
    site.post("hello", {"device": "RTX 3090", "catalog": CATALOG, "resumable": worker._resumable_here()})
    back = TrainRunModel.objects(id=slow["id"]).first()
    assert back.status == "queued" and back.target == "gpu2" and back.has_last

    # stopped while the worker still downloads the data: it gives up there
    TrainRunModel.objects(id=slow["id"]).update_one(set__status="stopped")
    early = t.post("/api/train/", json={"export_id": eid, "epochs": 5, "target": "gpu2"}).get_json()
    job = site.post("claim")
    assert job["id"] == early["id"]
    t.post(f"/api/train/{early['id']}/stop")
    run = SimpleNamespace(id=job["id"], task=job["task"], params=dict(job["params"]), epoch=0,
                          epochs=job["epochs"], dataset_names=job["dataset_names"])
    worker.execute(run, command=_fake_command(str(script)), io=worker.RemoteIO(site, job, run))
    gone = t.get(f"/api/train/{early['id']}").get_json()
    # (the export is kept from before: no new download)
    assert gone["status"] == "stopped" and gone["epoch"] == 0 and "is already here" in open(
        os.path.join(site_work(early["id"]), "train.log")).read()
    assert "Downloading export" in open(os.path.join(site_work(mine["id"]), "train.log")).read()

    # its server went away in the middle: stopping takes effect at once
    from database import TrainerStatusModel
    import datetime as dt
    lost = t.post("/api/train/", json={"export_id": eid, "epochs": 5, "target": "gpu2"}).get_json()
    assert site.post("claim")["id"] == lost["id"]
    TrainerStatusModel.objects(key="gpu2").update_one(set__seen_at=dt.datetime.utcnow() - dt.timedelta(minutes=5))
    assert t.post(f"/api/train/{lost['id']}/stop").get_json()["status"] == "stopped"
    # it comes back later: told to stop, its results are not taken
    assert site.post(f"runs/{lost['id']}/progress", {"lines": ["x"]})["stop"] is True
    assert site.post(f"runs/{lost['id']}/finish", data={"data": '{"status": "done"}'})["ignored"]

    # removing the server: what waited for it goes to any trainer
    TrainRunModel.objects(id=slow["id"]).update_one(set__status="queued")
    assert admin.delete("/api/worker/servers/gpu2").get_json()["success"]
    assert TrainRunModel.objects(id=slow["id"]).first().target == ""
    assert "gpu2" not in {x["name"] for x in t.get("/api/train/status").get_json()["trainers"]}
    try:
        site.post("claim")
        assert False, "a removed server's token still works"
    except PermissionError:
        pass
    TrainRunModel.objects(id=slow["id"]).update_one(set__status="stopped")


def test_worker_upload_in_pieces(tmp_path, monkeypatch):
    """Results go back in pieces (a proxy's upload limit does not matter);
    a piece that fails is sent again; nothing is removed if it never arrives."""
    from types import SimpleNamespace
    from trainer import runner, worker
    monkeypatch.setenv("MODELS_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(worker, "RETRY_SECONDS", 0)
    monkeypatch.setattr(worker, "PART_BYTES", 4)
    run = SimpleNamespace(id=778, task="detect", params={}, epoch=3, epochs=3, dataset_names=["x"])
    weights = os.path.join(runner.work_dir(778), "runs", "train", "weights")
    os.makedirs(weights)
    best = os.path.join(weights, "best.pt")
    open(best, "wb").write(b"0123456789")
    got, ends = {}, []

    class Site:
        flaky = 1

        def post(self, path, json_body=None, timeout=30, data=None, files=None):
            if "/part?" in path:
                name = path.split("file=")[1].split("&")[0]
                offset = int(path.split("offset=")[1])
                if name == "best" and offset == 4 and self.flaky:
                    self.flaky -= 1
                    raise ConnectionError("dropped")
                buf = got.setdefault(name, b"")
                if offset == len(buf):
                    got[name] = buf + data
                return {"size": len(got[name])}
            if path.endswith("/finish"):
                ends.append(data["data"])
            return {}

    io = worker.RemoteIO(Site(), {"id": 778}, run)
    io.finish("done", [{"epoch": 1}], "", "", best, False)
    assert got["best"] == b"0123456789" and len(got["archive"]) > 0
    assert '"uploaded": {"best": 10' in ends[0]
    assert not os.path.exists(runner.work_dir(778))  # all there: removed here

    # a site that never takes the pieces: the files stay here
    run.id = 779
    os.makedirs(os.path.join(runner.work_dir(779), "runs", "train", "weights"))
    best = os.path.join(runner.work_dir(779), "runs", "train", "weights", "best.pt")
    open(best, "wb").write(b"w")

    class Refusing(Site):
        def post(self, path, json_body=None, timeout=30, data=None, files=None):
            if "/part?" in path:
                raise ConnectionError("refused")
            return {}

    worker.RemoteIO(Refusing(), {"id": 779}, run).finish("done", [{"epoch": 1}], "", "", best, False)
    assert os.path.isfile(best)


def test_gpu_used_elsewhere(tmp_path, monkeypatch):
    """A GPU used outside this site (a training run by hand on that computer)
    is shown, and takes no queued training until it is free."""
    from database import ExportModel, RoleModel, TrainRunModel, UserModel
    from trainer import gpu as gpu_mod
    from trainer import runner
    from webserver import app

    # the readings
    now = {"name": "RTX 4070", "util": 3, "mem_used": 400, "mem_total": 16376, "procs": []}
    mon = gpu_mod.Monitor(reader=lambda: dict(now))
    assert mon.sample()["busy"] is False
    now["mem_used"] = 9000                      # someone's training holds memory
    assert mon.sample()["busy"] is True
    assert mon.sample(training=True)["busy"] is False   # our own training
    monkeypatch.setenv("GPU_BUSY_CHECK", "false")
    assert mon.sample()["busy"] is False
    monkeypatch.delenv("GPU_BUSY_CHECK")
    now.update(mem_used=400, util=95)           # busy, little memory: after a few readings
    assert [mon.sample()["busy"] for _ in range(3)] == [False, False, True]
    now["util"] = 0
    assert mon.sample()["busy"] is False
    assert gpu_mod.Monitor(reader=lambda: None).sample() is None   # no nvidia-smi

    # a worker whose GPU is used elsewhere gets nothing
    TrainRunModel.objects(status__in=["queued", "running"]).update(set__status="stopped")
    UserModel.objects(username="tr_gpu_admin").delete()
    UserModel(username="tr_gpu_admin", password=hash_password("pw"), name="a", is_admin=True).save()
    admin = app.test_client()
    admin.post("/api/user/login", json={"username": "tr_gpu_admin", "password": "pw"})
    admin.delete("/api/worker/servers/gpuB")
    token = admin.post("/api/worker/servers", json={"name": "gpuB"}).get_json()["token"]
    export = ExportModel(dataset_id=1, path="", tags=["YOLO"])
    export.save()
    run = TrainRunModel(export_id=export.id, task="detect", status="queued", target="gpuB", epochs=1)
    run.save()
    site = _TestSite(app.test_client(), token)
    site.post("hello", {"device": "RTX 4070", "catalog": CATALOG, "resumable": []})
    busy = {"name": "RTX 4070", "util": 97, "mem_used": 9000, "mem_total": 16376, "busy": True,
            "procs": [{"pid": 4242, "name": "python", "mem": 8600}]}
    assert site.post("claim", {"gpu": busy}) is None
    assert TrainRunModel.objects(id=run.id).first().status == "queued"
    shown = {t["name"]: t for t in admin.get("/api/train/status").get_json()["trainers"]}["gpuB"]
    assert shown["gpu"]["busy"] is True and shown["gpu"]["mem_used"] == 9000
    assert shown["gpu"]["procs"] == [{"pid": 4242, "name": "python", "mem": 8600}]
    # free again: it takes the run
    free = dict(busy, util=0, mem_used=300, busy=False, procs=[])
    job = site.post("claim", {"gpu": free})
    assert job["id"] == run.id
    shown = {t["name"]: t for t in admin.get("/api/train/status").get_json()["trainers"]}["gpuB"]
    assert shown["run_id"] == run.id and shown["gpu"]["busy"] is False
    TrainRunModel.objects(id=run.id).update(set__status="stopped")
    # this server's trainer reports its GPU too
    runner.heartbeat("RTX 3090", name="main", run_id=None, gpu=dict(busy))
    shown = {t["name"]: t for t in admin.get("/api/train/status").get_json()["trainers"]}["main"]
    assert shown["gpu"]["busy"] is True

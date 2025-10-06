import importlib.util
import sys
import threading
import time
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASYNC_APP_PATH = PROJECT_ROOT / "async-app.py"


class FakePixelStrip:
    def __init__(self, count, *args, **kwargs):
        self.count = count
        self.pixels = [None] * count

    def begin(self):
        pass

    def numPixels(self):
        return self.count

    def setPixelColor(self, index, color):
        if 0 <= index < self.count:
            self.pixels[index] = color

    def show(self):
        pass


def load_async_app_module():
    module_name = "async_app_under_test"
    sys.modules.pop(module_name, None)
    sys.modules.pop("async_app", None)
    for dep in [
        "clock_effects",
        "effects",
        "light_race",
        "embeddings",
        "colors",
    ]:
        sys.modules.pop(dep, None)

    project_root_str = str(PROJECT_ROOT)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    fake_ws281x = types.ModuleType("rpi_ws281x")
    fake_ws281x.PixelStrip = FakePixelStrip
    fake_ws281x.Color = lambda r, g, b: (r, g, b)
    sys.modules["rpi_ws281x"] = fake_ws281x

    spec = importlib.util.spec_from_file_location(module_name, ASYNC_APP_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def async_app_module():
    module = load_async_app_module()
    yield module
    module.stop_current_job()
    module.reset_stop_flags()


def test_effect_runner_runs_sync_job(async_app_module):
    run_event = threading.Event()

    async_app_module.jobs["unit_sync"] = lambda: run_event.set()

    try:
        async_app_module.effect_runner("unit_sync")
        thread = async_app_module.current_thread
        assert thread is not None
        thread.join(timeout=1)
        assert run_event.is_set()
        assert async_app_module.current_thread is None
        assert async_app_module.current_effect is None
    finally:
        async_app_module.jobs.pop("unit_sync", None)


def test_effect_runner_runs_async_job(async_app_module):
    run_event = threading.Event()

    async def sample_async_job():
        run_event.set()

    async_app_module.jobs["unit_async"] = lambda: sample_async_job()

    try:
        async_app_module.effect_runner("unit_async")
        thread = async_app_module.current_thread
        assert thread is not None
        thread.join(timeout=1)
        assert run_event.is_set()
        assert async_app_module.current_thread is None
        assert async_app_module.current_effect is None
    finally:
        async_app_module.jobs.pop("unit_async", None)


def test_stop_endpoint_without_job(async_app_module):
    client = async_app_module.app.test_client()
    response = client.post("/stop")

    assert response.status_code == 400
    assert response.get_json() == {"error": "No effect is currently running"}


def test_start_and_stop_blocking_job(async_app_module):
    started_event = threading.Event()
    stopped_event = threading.Event()

    def blocking_job():
        started_event.set()
        while not async_app_module.effects.stop_flag:
            time.sleep(0.01)
        stopped_event.set()

    async_app_module.jobs["unit_block"] = blocking_job

    client = async_app_module.app.test_client()

    try:
        start_response = client.post("/start", json={"effect": "unit_block"})
        assert start_response.status_code == 200
        assert started_event.wait(timeout=1)

        status_response = client.get("/status")
        assert status_response.get_json()["status"] == "running"
        assert status_response.get_json()["effect"] == "unit_block"

        stop_response = client.post("/stop")
        assert stop_response.status_code == 200
        assert stopped_event.wait(timeout=1)

        thread = async_app_module.current_thread
        if thread:
            thread.join(timeout=1)
        assert async_app_module.current_thread is None
        assert async_app_module.current_effect is None
    finally:
        async_app_module.jobs.pop("unit_block", None)
        async_app_module.reset_stop_flags()


def test_clocks_route_renders(async_app_module):
    client = async_app_module.app.test_client()
    response = client.get("/clocks")

    assert response.status_code == 200
    assert b"Clock Controller" in response.data


@pytest.mark.parametrize(
    ("job_name", "clock_attr"),
    [
        ("clock", "clock"),
        ("clock2", "clock2"),
        ("clock3", "clock3"),
        ("clock4", "clock4"),
        ("clock5", "clock5"),
        ("clock6", "clock6"),
    ],
)
def test_clock_jobs_dispatch_to_clock_effects(async_app_module, monkeypatch, job_name, clock_attr):
    call_event = threading.Event()

    def stub(strip):
        call_event.set()

    monkeypatch.setattr(async_app_module.clock_effects, clock_attr, stub)

    async_app_module.jobs[job_name]()

    assert call_event.is_set()


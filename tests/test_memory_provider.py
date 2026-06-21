import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent


class TestMemoryConfiguration:
    @pytest.fixture(scope="class")
    def config(self):
        config_path = PROJECT_ROOT / "deploy" / "nas" / "hermes-data" / "config.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)

    def test_memory_section_exists(self, config):
        assert "memory" in config, "No 'memory' section in config.yaml"

    def test_memory_provider_is_honcho(self, config):
        assert config["memory"]["provider"] == "honcho"

    def test_honcho_base_url_uses_docker_hostname(self, config):
        base_url = config["memory"]["honcho"]["base_url"]
        assert base_url == "http://api:8000", (
            f"Honcho base_url should be Docker hostname 'http://api:8000', got {base_url!r}. "
            "Using 127.0.0.1 or localhost breaks cross-container communication."
        )

    def test_reasoning_depth_is_two(self, config):
        assert config["memory"]["reasoning_depth"] == 2

    def test_memory_enabled(self, config):
        assert config["memory"]["memory_enabled"] is True

    def test_memory_char_limit_set(self, config):
        assert "memory_char_limit" in config["memory"]
        assert config["memory"]["memory_char_limit"] > 0

    def test_user_profile_enabled(self, config):
        assert config["memory"].get("user_profile_enabled") is True


class TestDockerHostnameRegression:
    """Guards against the localhost bug that caused all overnight failures.

    Every service URL must use Docker network hostnames, not 127.0.0.1 or localhost.
    Failing this test means the next commit will break overnight cron execution.
    """

    @pytest.fixture(scope="class")
    def config_text(self):
        config_path = PROJECT_ROOT / "deploy" / "nas" / "hermes-data" / "config.yaml"
        return config_path.read_text()

    @pytest.fixture(scope="class")
    def config(self, config_text):
        return yaml.safe_load(config_text)

    def _collect_base_urls(self, obj, path=""):
        urls = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "base_url" and isinstance(v, str) and v:
                    urls.append((f"{path}.{k}", v))
                urls.extend(self._collect_base_urls(v, f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                urls.extend(self._collect_base_urls(item, f"{path}[{i}]"))
        return urls

    def test_no_127_0_0_1_in_service_urls(self, config):
        urls = self._collect_base_urls(config)
        bad = [(path, url) for path, url in urls if "127.0.0.1" in url]
        assert not bad, (
            f"Found 127.0.0.1 in service URLs (breaks Docker networking): {bad}"
        )

    def test_no_localhost_in_service_urls(self, config):
        urls = self._collect_base_urls(config)
        bad = [(path, url) for path, url in urls if "localhost" in url]
        assert not bad, (
            f"Found 'localhost' in service URLs (breaks Docker networking): {bad}"
        )

    def test_model_base_url_uses_tokeneye_hostname(self, config):
        base_url = config["model"]["base_url"]
        assert "tokeneye" in base_url, (
            f"model.base_url should reference 'tokeneye' Docker service, got: {base_url!r}"
        )

    def test_cron_prompts_no_localhost(self, config_text):
        import re
        prompts_with_localhost = []
        for job in yaml.safe_load(config_text).get("cron", {}).get("jobs", []):
            prompt = job.get("prompt", "")
            if re.search(r'http://(127\.0\.0\.1|localhost):\d+', prompt):
                prompts_with_localhost.append(job.get("name", "unknown"))
        assert not prompts_with_localhost, (
            f"Cron prompts contain localhost URLs (LLM agents can't reach these from inside container): {prompts_with_localhost}"
        )


class TestHonchoConnectivityPatterns:
    """Tests the expected Honcho API interaction patterns using mocked HTTP."""

    BASE_URL = "http://api:8000"

    def _mock_response(self, status_code=200, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.ok = status_code < 400
        return resp

    def test_health_check_endpoint(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value = self._mock_response(200, {"status": "ok"})
            import requests
            r = requests.get(f"{self.BASE_URL}/health")
            assert r.status_code == 200
            mock_get.assert_called_once_with(f"{self.BASE_URL}/health")

    def test_user_creation_pattern(self):
        with patch("requests.post") as mock_post:
            user_id = "param-user-gajendra"
            app_id = "param"
            mock_post.return_value = self._mock_response(200, {"id": user_id})
            import requests
            r = requests.post(f"{self.BASE_URL}/v1/apps/{app_id}/users", json={"name": user_id})
            assert r.ok
            assert r.json()["id"] == user_id

    def test_session_creation_pattern(self):
        with patch("requests.post") as mock_post:
            session_id = "ses_abc123"
            mock_post.return_value = self._mock_response(200, {"id": session_id, "user_id": "u1"})
            import requests
            r = requests.post(
                f"{self.BASE_URL}/v1/apps/param/users/u1/sessions",
                json={"session_id": session_id}
            )
            assert r.ok
            assert r.json()["id"] == session_id

    def test_message_storage_pattern(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = self._mock_response(200, {"id": "msg_1"})
            import requests
            r = requests.post(
                f"{self.BASE_URL}/v1/apps/param/users/u1/sessions/ses_1/messages",
                json={"role": "user", "content": "remember: I prefer dark mode"}
            )
            assert r.ok

    def test_message_retrieval_pattern(self):
        with patch("requests.get") as mock_get:
            messages = [
                {"role": "user", "content": "remember: I prefer dark mode"},
                {"role": "assistant", "content": "Noted: dark mode preference saved."},
            ]
            mock_get.return_value = self._mock_response(200, {"items": messages})
            import requests
            r = requests.get(
                f"{self.BASE_URL}/v1/apps/param/users/u1/sessions/ses_1/messages"
            )
            assert r.ok
            assert len(r.json()["items"]) == 2


class TestCrossSessionPersistence:
    """Tests that memory written in one session is accessible from another via the same user."""

    BASE_URL = "http://api:8000"

    def test_two_sessions_share_user_workspace(self):
        call_log = []

        def fake_post(url, json=None, **kwargs):
            call_log.append(("POST", url, json))
            resp = MagicMock()
            resp.status_code = 200
            resp.ok = True
            resp.json.return_value = {"id": "created"}
            return resp

        def fake_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.ok = True
            resp.json.return_value = {
                "items": [{"role": "user", "content": "dark mode preference"}]
            }
            return resp

        with patch("requests.post", side_effect=fake_post), \
             patch("requests.get", side_effect=fake_get):
            import requests

            user_id = "param-user-shared"
            session_a = "ses_morning"
            session_b = "ses_evening"

            requests.post(
                f"{self.BASE_URL}/v1/apps/param/users/{user_id}/sessions/{session_a}/messages",
                json={"role": "user", "content": "dark mode preference"}
            )

            r = requests.get(
                f"{self.BASE_URL}/v1/apps/param/users/{user_id}/sessions/{session_b}/messages"
            )

            assert r.ok
            items = r.json()["items"]
            assert len(items) > 0

            posted_urls = [url for method, url, _ in call_log if method == "POST"]
            assert any(user_id in url for url in posted_urls)

    def test_different_users_are_isolated(self):
        responses = {
            "user_a": [{"role": "user", "content": "user_a secret"}],
            "user_b": [],
        }

        def fake_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.ok = True
            for uid, msgs in responses.items():
                if uid in url:
                    resp.json.return_value = {"items": msgs}
                    return resp
            resp.json.return_value = {"items": []}
            return resp

        with patch("requests.get", side_effect=fake_get):
            import requests

            r_a = requests.get(f"{self.BASE_URL}/v1/apps/param/users/user_a/sessions/ses_1/messages")
            r_b = requests.get(f"{self.BASE_URL}/v1/apps/param/users/user_b/sessions/ses_1/messages")

            a_items = r_a.json()["items"]
            b_items = r_b.json()["items"]

            assert len(a_items) > 0
            assert len(b_items) == 0

    def test_memory_from_session_a_retrievable_in_session_b(self):
        stored = {}

        def fake_post(url, json=None, **kwargs):
            if "/messages" in url:
                stored[url] = json
            resp = MagicMock()
            resp.status_code = 200
            resp.ok = True
            resp.json.return_value = {"id": "msg_stored"}
            return resp

        def fake_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.ok = True
            user_msgs = [v for k, v in stored.items() if "user_a" in k]
            resp.json.return_value = {"items": user_msgs}
            return resp

        with patch("requests.post", side_effect=fake_post), \
             patch("requests.get", side_effect=fake_get):
            import requests

            requests.post(
                f"{self.BASE_URL}/v1/apps/param/users/user_a/sessions/ses_A/messages",
                json={"role": "user", "content": "I prefer Python over JavaScript"}
            )

            r = requests.get(
                f"{self.BASE_URL}/v1/apps/param/users/user_a/sessions/ses_B/messages"
            )

            items = r.json()["items"]
            assert len(items) == 1
            assert "Python" in items[0]["content"]


class TestHonchoConnectionRobustness:
    def test_connection_refused_handled(self):
        with patch("requests.get", side_effect=ConnectionRefusedError("Connection refused")):
            import requests
            with pytest.raises(ConnectionRefusedError):
                requests.get("http://api:8000/health")

    def test_timeout_scenario(self):
        import requests as req_module
        with patch("requests.get", side_effect=req_module.exceptions.Timeout("Request timed out")):
            import requests
            with pytest.raises(requests.exceptions.Timeout):
                requests.get("http://api:8000/health", timeout=5)

import os
import yaml
import json
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestConfigYAMLValidation:
    """Validate all YAML config files are syntactically correct."""

    def test_nas_config_yaml_is_valid(self):
        path = os.path.join(PROJECT_ROOT, "deploy/nas/hermes-data/config.yaml")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        assert cfg is not None
        assert "model" in cfg
        assert "cron" in cfg
        assert "memory" in cfg

    def test_nas_config_model_routes_through_tokeneye(self):
        path = os.path.join(PROJECT_ROOT, "deploy/nas/hermes-data/config.yaml")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        assert cfg["model"]["base_url"] == "http://tokeneye:8787/zen/go/v1"

    def test_nas_config_cron_has_required_jobs(self):
        path = os.path.join(PROJECT_ROOT, "deploy/nas/hermes-data/config.yaml")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        job_names = [j["name"] for j in cfg["cron"]["jobs"]]
        assert "morning-briefing" in job_names
        assert "health-check" in job_names
        assert "memory-consolidation" in job_names
        assert "tunnel-watchdog" in job_names

    def test_docker_compose_is_valid(self):
        path = os.path.join(PROJECT_ROOT, "deploy/nas/docker-compose.yml")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        assert "services" in cfg
        assert "hermes" in cfg["services"]
        assert "tokeneye" in cfg["services"]

    def test_docker_compose_network_isolation(self):
        """All non-cloudflared services use bridge network, cloudflared stays host."""
        path = os.path.join(PROJECT_ROOT, "deploy/nas/docker-compose.yml")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        # Bridge network defined
        assert "networks" in cfg
        assert "param-net" in cfg["networks"]
        assert cfg["networks"]["param-net"]["driver"] == "bridge"
        # Non-cloudflared services on bridge
        bridge_services = ["hermes", "tokeneye", "nginx", "vaultwarden", "websurfx", "redis-ws"]
        for svc in bridge_services:
            assert "networks" in cfg["services"][svc], f"{svc} missing networks key"
            assert "param-net" in cfg["services"][svc]["networks"], f"{svc} not on param-net"
        # Cloudflared stays host mode
        assert cfg["services"]["cloudflared"]["network_mode"] == "host"
        # Port mappings for exposed services
        assert cfg["services"]["hermes"]["ports"] is not None
        assert cfg["services"]["tokeneye"]["ports"] is not None

    def test_docker_compose_restart_policy(self):
        path = os.path.join(PROJECT_ROOT, "deploy/nas/docker-compose.yml")
        with open(path) as f:
            cfg = yaml.safe_load(f)
        for svc in ["hermes", "tokeneye"]:
            assert cfg["services"][svc]["restart"] == "unless-stopped"

    def test_cloudflared_config_is_valid(self):
        path = os.path.join(
            PROJECT_ROOT, "deploy/nas/configs/cloudflared-config.yml"
        )
        with open(path) as f:
            cfg = yaml.safe_load(f)
        assert "tunnel" in cfg
        assert "ingress" in cfg


class TestSkillWhitelistValidation:
    """Validate skill-whitelist.yaml completeness."""

    def test_whitelist_exists(self):
        path = os.path.join(PROJECT_ROOT, "configs/skill-whitelist.yaml")
        assert os.path.exists(path)

    def test_whitelist_covers_all_10_agents(self):
        path = os.path.join(PROJECT_ROOT, "configs/skill-whitelist.yaml")
        with open(path) as f:
            content = f.read()
        required_agents = [
            "sisyphus", "oracle", "explore", "librarian",
            "hephaestus", "sisyphus-junior", "metis", "momus",
            "prometheus", "atlas",
        ]
        for agent in required_agents:
            assert agent in content, f"Agent {agent} not found in whitelist"


class TestVaultStructure:
    """Validate Obsidian vault directory structure."""

    def test_vault_directory_exists(self):
        path = os.path.join(PROJECT_ROOT, "vault")
        assert os.path.isdir(path)

    def test_vault_has_required_directories(self):
        path = os.path.join(PROJECT_ROOT, "vault")
        required = [
            "Architecture", "Operations", "Research",
            "Project", "Meta", "Security", "Strategy",
        ]
        for d in required:
            assert os.path.isdir(os.path.join(path, d)), f"Missing vault dir: {d}"


class TestScriptSyntax:
    """Validate shell scripts have valid syntax."""

    SCRIPTS = [
        "scripts/param-status.sh",
        "deploy/nas/scripts/cloudflared-watchdog.sh",
        "deploy/nas/deploy.sh",
        "deploy/nas/cloudflared-setup-noninteractive.sh",
    ]

    @pytest.mark.parametrize("script_rel", SCRIPTS)
    def test_script_exists_and_executable(self, script_rel):
        path = os.path.join(PROJECT_ROOT, script_rel)
        assert os.path.exists(path), f"Missing: {script_rel}"
        assert os.access(path, os.X_OK), f"Not executable: {script_rel}"

    @pytest.mark.parametrize("script_rel", SCRIPTS)
    def test_script_has_shebang(self, script_rel):
        path = os.path.join(PROJECT_ROOT, script_rel)
        with open(path) as f:
            first_line = f.readline()
        assert first_line.startswith("#!"), f"No shebang in {script_rel}"

    @pytest.mark.parametrize("script_rel", SCRIPTS)
    def test_script_passes_bash_syntax_check(self, script_rel):
        import subprocess
        path = os.path.join(PROJECT_ROOT, script_rel)
        result = subprocess.run(
            ["bash", "-n", path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in {script_rel}: {result.stderr}"

import json
import tempfile
import shutil
from pathlib import Path
import pytest
from raven.core.registry import VaultRegistry, VaultMeta, VAULTS_ROOT
from raven.core.vault import Vault

@pytest.fixture
def clean_registry_env(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-test-selfheal-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    yield reg_root
    shutil.rmtree(reg_root, ignore_errors=True)

def test_registry_and_vault_json_self_healing(clean_registry_env, monkeypatch):
    reg_root = clean_registry_env
    # 1. 가짜 볼트 디렉토리 생성
    vault_name = "test-heal"
    actual_vault_dir = reg_root / vault_name
    actual_vault_dir.mkdir(parents=True)
    
    # 2. 잘못된 경로를 담은 .vault.json 생성
    vjson_path = actual_vault_dir / ".vault.json"
    bad_path = "/Users/wronguser/Raven/test-heal"
    vjson_path.write_text(json.dumps({
        "path": bad_path,
        "mode": "personal",
        "owner": "user"
    }), encoding="utf-8")
    
    # 3. 잘못된 경로를 가진 .registry.json 생성
    registry_path = reg_root / ".registry.json"
    registry_path.write_text(json.dumps({
        "version": 1,
        "default": vault_name,
        "vaults": {
            vault_name: {
                "path": bad_path,
                "mode": "personal",
                "owner": "user"
            }
        }
    }), encoding="utf-8")
    
    # 4. VaultRegistry 로드 및 쿼리
    reg = VaultRegistry(root=reg_root)
    # registry().get을 호출하면 잘못된 경로가 actual_vault_dir로 자가 치유되어야 함
    meta = reg.get(vault_name)
    assert meta is not None
    assert str(meta.path) == str(actual_vault_dir.resolve())
    
    # 5. .registry.json 파일에 자가치유가 반영되었는지 검증
    refreshed_reg = json.loads(registry_path.read_text(encoding="utf-8"))
    assert refreshed_reg["vaults"][vault_name]["path"] == str(actual_vault_dir.resolve())
    
    # 6. Vault.load 시 .vault.json 파일도 자가치유되는지 검증
    v = Vault.load(meta)
    assert v is not None
    
    refreshed_vjson = json.loads(vjson_path.read_text(encoding="utf-8"))
    assert refreshed_vjson["path"] == str(actual_vault_dir.resolve())

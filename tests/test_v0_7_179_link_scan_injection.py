"""link_module의 rglob 3회 제거 — docs/issues/link-module-rglob-3회-잔여.md 마감.

v0.7.68이 `lint.run_all()`의 중복 스캔을 `_ScanCache`로 없앴지만,
`_legacy_link_issues()`가 부르는 `find_broken` / `find_broken_intent` /
`find_missing`은 각자 vault를 rglob하고 파일마다 `read_text()`를 다시 했다 —
캐시 적용 범위 밖이었다.

이 파일은 두 가지를 동시에 고정한다:
1. **characterization** — 주입 파라미터가 생겨도 세 함수의 결과와 lint #1-#3
   issue 집합이 그대로여야 한다. (변경 전 코드에서도 통과한다.)
2. **I/O 감소 증명** — `run_all()` 1회에서 같은 content 페이지를 두 번 이상
   읽지 않는다. 리팩터링이 아니라 실제 중복 제거임을 증거로 남긴다.

주의: lint의 `_all_pages()`는 `_meta/`를 포함하고 `_archive/`를 제외하지만
link_module은 `content_root` 전체를 본다. 스코프가 다르므로 `_all_pages()`
목록을 그대로 주입하면 성능 개선이 아니라 **lint 결과 변경**이 된다 —
`test_meta_pages_are_not_pulled_into_link_checks`가 그 경계를 지킨다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import link as link_module
from raven.core import lint as lint_module
from raven.core.contracts import write_page
from raven.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-linkscan-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-linkscan-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("linkscan", target_root / "linkscan")

    write_page(
        v, "content/alpha",
        "alpha links to [[content/beta]] and [[content/ghost]] plainly here",
        title="Alpha", type="concept", normalize=False,
    )
    write_page(
        v, "content/beta",
        "beta marks [[content/gone]]! as broken and [[content/later]]? as pending",
        title="Beta", type="concept", normalize=False,
    )
    write_page(
        v, "content/gone",
        "gone actually exists, which makes beta's broken intent wrong",
        title="Gone", type="concept", normalize=False,
    )
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def _sorted(rows: list[dict]) -> list[tuple]:
    return sorted((r["source_slug"], r["target"], r["intent"]) for r in rows)


class TestCharacterization:
    """변경 전 코드에서도 통과해야 하는 계약 — 주입은 결과를 바꾸지 않는다."""

    def test_find_broken_reports_missing_plain_target(self, vault):
        assert _sorted(link_module.find_broken(vault)) == [
            ("content/alpha", "content/ghost", "auto")
        ]

    def test_find_broken_intent_reports_false_positive(self, vault):
        assert _sorted(link_module.find_broken_intent(vault)) == [
            ("content/beta", "content/gone", "broken")
        ]

    def test_find_missing_reports_intentional_placeholder(self, vault):
        assert _sorted(link_module.find_missing(vault)) == [
            ("content/beta", "content/later", "missing")
        ]

    def test_single_slug_query_path_still_works(self, vault):
        assert _sorted(link_module.find_broken(vault, slug="content/alpha")) == [
            ("content/alpha", "content/ghost", "auto")
        ]
        assert link_module.find_broken(vault, slug="content/beta") == []

    def test_lint_link_issues_unchanged(self, vault):
        result = lint_module.run_all(vault)
        ids = {i["id"] for i in result["issues"] if i["id"] in {"#1", "#2", "#3"}}
        assert ids == {"#1", "#2", "#3"}

        by_id = {}
        for issue in result["issues"]:
            if issue["id"] in {"#1", "#2", "#3"}:
                by_id.setdefault(issue["id"], []).append((issue["slug"], issue["target"]))
        assert by_id["#1"] == [("content/alpha", "content/ghost")]
        assert by_id["#2"] == [("content/beta", "content/gone")]
        assert by_id["#3"] == [("content/beta", "content/later")]


class TestInjectedPages:
    def test_injected_pages_replace_the_vault_scan(self, vault):
        """주입한 목록만 보는지 확인 — 주입이 무시되면 이 단언이 깨진다."""
        pages = [("content/alpha", "alpha links to [[content/nowhere]] in an injected body")]

        assert _sorted(link_module.find_broken(vault, pages=pages)) == [
            ("content/alpha", "content/nowhere", "auto")
        ]

    def test_injected_empty_list_is_not_confused_with_none(self, vault):
        """빈 목록 = '스캔할 페이지 없음'이고, None = '직접 스캔하라'다."""
        assert link_module.find_broken(vault, pages=[]) == []
        assert link_module.find_broken(vault) != []

    def test_slug_argument_wins_over_injected_pages(self, vault):
        """단일 페이지 조회는 공개 API 계약이므로 주입보다 우선한다."""
        pages = [("content/beta", "irrelevant injected body without any wikilink")]

        assert _sorted(link_module.find_broken(vault, slug="content/alpha", pages=pages)) == [
            ("content/alpha", "content/ghost", "auto")
        ]


class TestIoReduction:
    def test_run_all_reads_each_content_page_once(self, vault, monkeypatch):
        """중복 제거 증명: 변경 전에는 link 함수 3개가 같은 파일을 각각 다시 읽었다."""
        reads: dict[Path, int] = {}
        original = Path.read_text

        def counting_read_text(self, *args, **kwargs):
            if self.suffix == ".md":
                reads[self] = reads.get(self, 0) + 1
            return original(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", counting_read_text)
        lint_module.run_all(vault)

        content_reads = {
            path: count
            for path, count in reads.items()
            if "content" in path.parts and count > 1
        }
        assert content_reads == {}

    def test_content_root_is_globbed_once_per_run(self, vault, monkeypatch):
        """rglob 3회 → 1회. 스캔 목록 자체도 캐시를 타야 한다."""
        globs: list[Path] = []
        original = Path.rglob

        def counting_rglob(self, pattern, *args, **kwargs):
            if pattern == "*.md":
                globs.append(self)
            return original(self, pattern, *args, **kwargs)

        monkeypatch.setattr(Path, "rglob", counting_rglob)
        lint_module.run_all(vault)

        assert globs.count(vault.content_root) == 1


def test_meta_pages_are_not_pulled_into_link_checks(vault):
    """lint의 `_all_pages()`(=_meta 포함)를 그대로 주입하면 lint 결과가 바뀐다.

    link 체크의 스코프는 `content_root`다. 이 가드가 스코프 혼입을 막는다.
    """
    meta_dir = vault.meta_root
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "note.md").write_text(
        "meta note pointing at [[content/absent-on-purpose]] plainly\n", encoding="utf-8"
    )

    broken = link_module.find_broken(vault)

    assert all(not r["source_slug"].startswith("_meta") for r in broken)
    result = lint_module.run_all(vault)
    link_slugs = {i["slug"] for i in result["issues"] if i["id"] in {"#1", "#2", "#3"}}
    assert all(not s.startswith("_meta") for s in link_slugs)

"""Tests for translator.py.

Deliberately small: only behaviour that would actually hurt if it broke.
Hand-written fakes instead of unittest.mock — fakes survive refactoring of
call signatures, mock assertions do not.
"""

import unittest

from translator import (
    BatchPlanner,
    BlockAligner,
    Config,
    MarkdownSplitter,
    ProviderConfig,
    PromptConfig,
    QuotaExhausted,
    SegmentCodec,
    SourceConfig,
    StateConfig,
    TargetConfig,
    TranslationPipeline,
    TranslationRequest,
    chain_translate,
)

# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


class FakeGit:
    """Serves file contents per (ref, path) and records write operations."""

    def __init__(self, head, trees, changes):
        self._head = head
        self._trees = trees  # {ref: {path: text}}
        self._changes = changes  # [(status, path)]
        self.commits = []
        self.pushed = []
        self.branch = None

    def rev_parse(self, ref):
        return self._head

    def show(self, ref, path):
        try:
            return self._trees[ref][path]
        except KeyError:
            raise FileNotFoundError(f"{ref}:{path}")

    def diff_name_status(self, base, head, patterns):
        return list(self._changes)

    def create_branch(self, name):
        self.branch = name

    def commit(self, paths, message):
        self.commits.append((tuple(paths), message))

    def push(self, branch):
        self.pushed.append(branch)


class FakeFS:
    def __init__(self, files=None):
        self.files = dict(files or {})

    def read(self, path):
        return self.files[path]

    def write(self, path, text):
        self.files[path] = text

    def exists(self, path):
        return path in self.files

    def remove(self, path):
        self.files.pop(path, None)


class FakeProvider:
    """Echoes each requested segment back as RU(<source>)."""

    def __init__(self, codec, fail_with=None, drop_segments=()):
        self.codec = codec
        self.calls = 0
        self.translated_sources = []
        self._fail_with = fail_with
        self._drop = set(drop_segments)

    def translate(self, request):
        self.calls += 1
        if self._fail_with is not None:
            raise self._fail_with
        parts = []
        for seg_id, source in request.segments.items():
            if seg_id in self._drop:
                continue
            self.translated_sources.append(source)
            parts.append(self.codec.wrap(seg_id, f"RU({source})"))
        return "\n".join(parts)


class FakePRClient:
    def __init__(self):
        self.created = None
        self.ready = False
        self.body = None

    def create_draft(self, branch, base, title, body, label):
        self.created = branch
        self.body = body
        return 42

    def mark_ready(self, number):
        self.ready = True

    def update_body(self, number, body):
        self.body = body


class FakeClock:
    def stamp(self):
        return "20260101-000000"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def make_config(**overrides):
    cfg = Config(
        source=SourceConfig(
            ref="origin/main",
            include=["*.md"],
            exclude_paths=[".github"],
            exclude_files=["readme.md"],
        ),
        target=TargetConfig(
            branch="ru",
            language="Russian",
            branch_prefix="translate/sync-",
            pr_label="translate",
            pr_title="auto",
            pr_body_template="{translated}|{skipped}|{pending}",
        ),
        state=StateConfig(
            sync_file=".github/sync.txt", pending_file=".github/pending.txt"
        ),
        prompt=PromptConfig(
            template="{language}\n{glossary}\n{source}\n{existing_translation}",
            glossary={},
            context_mode="full",
            window_blocks=20,
            max_request_chars=100_000,
        ),
        providers=[ProviderConfig(name="gemini", model="m", api_key_env="K")],
    )
    return cfg if not overrides else cfg.replace(**overrides)


def build_pipeline(base_tree, head_tree, working, changes, provider=None, config=None):
    """Wires a pipeline over fakes. base_tree is the source at last sync."""
    cfg = config or make_config()
    codec = SegmentCodec()
    git = FakeGit(
        head="bbbbbbb2222222",
        trees={"origin/main": head_tree, "aaaaaaa1111111": base_tree},
        changes=changes,
    )
    fs = FakeFS({**working, ".github/sync.txt": "aaaaaaa1111111"})
    prov = provider if provider is not None else FakeProvider(codec)
    pipeline = TranslationPipeline(
        config=cfg,
        git=git,
        fs=fs,
        translate=lambda req: prov.translate(req),
        pull_requests=FakePRClient(),
        clock=FakeClock(),
    )
    return pipeline, git, fs, prov


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


class TestMarkdownSplitter(unittest.TestCase):
    def test_split_join_round_trip_is_byte_exact(self):
        splitter = MarkdownSplitter()
        samples = [
            "# Title\n\nSome text.\n\n```go\nfunc main() {}\n\nstill code\n```\n\nEnd.\n",
            "no trailing newline",
            "a\n\n\n\nb\n",
            "",
            "\n\nleading blanks\n",
        ]
        for text in samples:
            with self.subTest(text=text[:20]):
                doc = splitter.split(text)
                self.assertEqual(doc.render(), text)

    def test_fenced_code_stays_one_block(self):
        doc = MarkdownSplitter().split("intro\n\n```go\na\n\nb\n```\n\nouttro\n")
        self.assertEqual(len(doc.blocks), 3)
        self.assertIn("a\n\nb", doc.blocks[1].text)


class TestIncrementalMerge(unittest.TestCase):
    def test_manual_edit_in_unchanged_block_survives(self):
        base = "A para.\n\nB para.\n\nC para.\n"
        head = "A para.\n\nB para CHANGED.\n\nC para.\n"
        ru = "Ручной перевод A.\n\nПеревод B.\n\nПеревод C.\n"

        pipeline, _, fs, prov = build_pipeline(
            base_tree={"ch.md": base},
            head_tree={"ch.md": head},
            working={"ch.md": ru},
            changes=[("M", "ch.md")],
        )
        result = pipeline.run()

        self.assertEqual(result.translated, ["ch.md"])
        out = fs.files["ch.md"]
        self.assertIn("Ручной перевод A.", out)
        self.assertIn("Перевод C.", out)
        self.assertIn("RU(B para CHANGED.)", out)
        self.assertNotIn("Перевод B.", out)

    def test_only_changed_blocks_are_sent_for_translation(self):
        base = "A.\n\nB.\n\nC.\n"
        head = "A.\n\nB2.\n\nC.\n"
        pipeline, _, _, prov = build_pipeline(
            base_tree={"ch.md": base},
            head_tree={"ch.md": head},
            working={"ch.md": "ra.\n\nrb.\n\nrc.\n"},
            changes=[("M", "ch.md")],
        )
        pipeline.run()
        self.assertEqual(prov.translated_sources, ["B2."])

    def test_block_deleted_upstream_disappears_from_translation(self):
        pipeline, _, fs, prov = build_pipeline(
            base_tree={"ch.md": "A.\n\nB.\n\nC.\n"},
            head_tree={"ch.md": "A.\n\nC.\n"},
            working={"ch.md": "ra.\n\nrb.\n\nrc.\n"},
            changes=[("M", "ch.md")],
        )
        pipeline.run()
        out = fs.files["ch.md"]
        self.assertNotIn("rb.", out)
        self.assertIn("ra.", out)
        self.assertIn("rc.", out)
        self.assertEqual(prov.calls, 0, "nothing new to translate")

    def test_unalignable_file_is_skipped_and_left_untouched(self):
        original_ru = "only.\n\ntwo.\n"
        pipeline, _, fs, _ = build_pipeline(
            base_tree={"ch.md": "one.\n\ntwo.\n\nthree.\n\nfour.\n\nfive.\n"},
            head_tree={"ch.md": "one X.\n\ntwo.\n\nthree.\n\nfour.\n\nfive.\n"},
            working={"ch.md": original_ru},
            changes=[("M", "ch.md")],
        )
        result = pipeline.run()
        self.assertIn("ch.md", result.skipped)
        self.assertEqual(fs.files["ch.md"], original_ru)


class TestResilience(unittest.TestCase):
    def test_malformed_response_only_fails_its_own_file(self):
        codec = SegmentCodec()
        # segment 1 belongs to a.md, segment 2 to b.md; drop the second one
        provider = FakeProvider(codec, drop_segments=(2,))
        pipeline, _, fs, _ = build_pipeline(
            base_tree={"a.md": "A.\n", "b.md": "B.\n"},
            head_tree={"a.md": "A2.\n", "b.md": "B2.\n"},
            working={"a.md": "ra.\n", "b.md": "rb.\n"},
            changes=[("M", "a.md"), ("M", "b.md")],
            provider=provider,
        )
        result = pipeline.run()
        self.assertEqual(result.translated, ["a.md"])
        self.assertEqual(result.pending, ["b.md"])
        self.assertEqual(fs.files["b.md"], "rb.\n", "untouched on bad response")

    def test_quota_exhausted_falls_over_to_next_provider(self):
        codec = SegmentCodec()
        dead = FakeProvider(codec, fail_with=QuotaExhausted("daily limit"))
        alive = FakeProvider(codec)
        request = TranslationRequest(prompt="p", segments={1: "hello"})

        out = chain_translate([dead.translate, alive.translate], request)

        self.assertEqual(alive.calls, 1)
        self.assertIn("RU(hello)", out)

    def test_chain_reraises_when_every_provider_is_exhausted(self):
        codec = SegmentCodec()
        a = FakeProvider(codec, fail_with=QuotaExhausted("x"))
        b = FakeProvider(codec, fail_with=QuotaExhausted("y"))
        with self.assertRaises(QuotaExhausted):
            chain_translate(
                [a.translate, b.translate],
                TranslationRequest(prompt="p", segments={1: "s"}),
            )


class TestBatchPlanner(unittest.TestCase):
    def test_small_files_share_a_batch_and_large_one_travels_alone(self):
        planner = BatchPlanner(max_chars=100)
        items = [("a.md", 10), ("b.md", 10), ("big.md", 500), ("c.md", 10)]
        batches = planner.plan(items)
        grouped = [[path for path, _ in batch] for batch in batches]
        self.assertIn(["a.md", "b.md", "c.md"], grouped)
        self.assertIn(["big.md"], grouped)


if __name__ == "__main__":
    unittest.main()

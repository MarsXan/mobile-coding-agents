import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import fixtures
from mobilekit import adopt, verify


class HookProcessTests(unittest.TestCase):
    """Drive the hooks exactly as Claude Code does: JSON on stdin, JSON on stdout."""

    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="mobile-coding-agents-data-")
        self.addCleanup(shutil.rmtree, self.data, True)

    def hook(self, project, event, payload=None, session="s1"):
        body = {"session_id": session, "cwd": project.root, "hook_event_name": event}
        body.update(payload or {})
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=self.data, CLAUDE_PROJECT_DIR=project.root)
        proc = subprocess.run([sys.executable, fixtures.BIN, "hook", event], input=json.dumps(body).encode(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return proc.stdout.decode()

    def decision(self, output):
        return json.loads(output)["hookSpecificOutput"] if output.strip() else None

    def test_session_start_prints_project_facts(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        out = self.hook(project, "session-start", {"source": "startup"})
        self.assertIn("minimum iOS 15.0", out)
        self.assertIn("mobile verify", out)
        self.assertIn("No code map exists yet", out)
        self.assertLessEqual(len(out.splitlines()), 9)
        project.write("docs/agent/CODEMAP.md", "# map\n")
        self.assertIn("Code map: docs/agent/CODEMAP.md", self.hook(project, "session-start", {"source": "resume"}))

    def test_every_hook_is_silent_outside_a_mobile_project(self):
        project = fixtures.Project(git=True)
        self.addCleanup(project.cleanup)
        project.write("README.md", "hello\n")
        project.commit("init")
        self.assertEqual(self.hook(project, "session-start", {"source": "startup"}), "")
        self.assertEqual(self.hook(project, "pre-bash", {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}), "")
        self.assertEqual(self.hook(project, "pre-edit", {"tool_name": "Write", "tool_input": {"file_path": project.root + "/.env", "content": "x"}}), "")
        self.assertEqual(self.hook(project, "stop"), "")
        self.assertFalse(project.exists(".mobile-coding-agents"))

    def test_pre_bash_denies_and_asks_in_the_documented_shape(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        out = self.decision(self.hook(project, "pre-bash", {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}))
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("protected branch", out["permissionDecisionReason"])
        out = self.decision(self.hook(project, "pre-bash", {"tool_name": "Bash", "tool_input": {"command": "bundle exec fastlane beta"}}))
        self.assertEqual(out["permissionDecision"], "ask")
        self.assertEqual(self.hook(project, "pre-bash", {"tool_name": "Bash", "tool_input": {"command": "xcodebuild -scheme App build"}}), "")

    def test_pre_edit_denies_generated_files_and_secrets(self):
        project = fixtures.flutter_project(git=True)
        self.addCleanup(project.cleanup)
        out = self.decision(self.hook(project, "pre-edit", {"tool_name": "Edit", "tool_input": {
            "file_path": project.root + "/lib/model.g.dart", "old_string": "a", "new_string": "b"}}))
        self.assertEqual(out["permissionDecision"], "deny")
        out = self.decision(self.hook(project, "pre-edit", {"tool_name": "Write", "tool_input": {
            "file_path": project.root + "/lib/keys.dart", "content": "const k = 'sk_live_" + "a1B2c3D4e5F6g7H8i9J0k1L2" + "';"}}))
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertEqual(self.hook(project, "pre-edit", {"tool_name": "Write", "tool_input": {
            "file_path": project.root + "/lib/ok.dart", "content": "const ok = true;"}}), "")

    def test_post_edit_notes_are_given_once_per_session(self):
        project = fixtures.android_project(git=True)
        self.addCleanup(project.cleanup)
        payload = {"tool_name": "Edit", "tool_input": {
            "file_path": project.root + "/app/src/main/java/com/example/data/User.kt", "old_string": "val name: String,", "new_string": "val name: String,\n    val nick: String?,"}}
        first = self.decision(self.hook(project, "post-edit", payload))
        self.assertEqual(first["hookEventName"], "PostToolUse")
        self.assertIn("stored on users' devices", first["additionalContext"])
        self.assertEqual(self.hook(project, "post-edit", payload), "")
        self.assertIn("stored on users' devices", self.hook(project, "post-edit", payload, session="s2"))

    def test_stop_gate_blocks_once_per_unverified_state(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        self.hook(project, "session-start", {"source": "startup"})
        self.assertEqual(self.hook(project, "stop"), "", "nothing changed yet")
        project.write("README.md", "docs only\n")
        self.assertEqual(self.hook(project, "stop"), "", "non-source change")
        project.write("App/Model.swift", "struct Model { let id: String }\n")
        blocked = json.loads(self.hook(project, "stop"))
        self.assertEqual(blocked["decision"], "block")
        self.assertIn("mobile verify", blocked["reason"])
        self.assertEqual(self.hook(project, "stop", {"stop_hook_active": True}), "")
        self.assertEqual(self.hook(project, "stop"), "", "already told for this state")
        project.write("App/Model.swift", "struct Model { let id: UUID }\n")
        self.assertIn("block", self.hook(project, "stop"), "a new state is a new reminder")

    def test_stop_gate_passes_after_verify_and_respects_configuration(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        self.hook(project, "session-start", {"source": "startup"})
        project.write("App/Model.swift", "struct Model { let id: String }\n")
        verify.write_stamp(project.root, "quick", ["ios"])
        self.assertEqual(self.hook(project, "stop"), "")

        other = fixtures.ios_project(git=True)
        self.addCleanup(other.cleanup)
        other.write(".mobile-coding-agents.json", '{"verifyGate": "remind"}')
        self.hook(other, "session-start", {"source": "startup"}, session="s3")
        other.write("App/Model.swift", "struct Model { let id: String }\n")
        reminded = json.loads(self.hook(other, "stop", session="s3"))
        self.assertEqual(reminded["hookSpecificOutput"]["hookEventName"], "Stop")
        self.assertNotIn("decision", reminded)

    def test_keel_governed_project_keeps_bash_guard_and_drops_the_stop_gate(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write(".keel/config.json", '{"keel": "0.1"}')
        self.assertIn("governed by Keel", self.hook(project, "session-start", {"source": "startup"}))
        project.write("App/Model.swift", "struct Model { let id: String }\n")
        self.assertEqual(self.hook(project, "stop"), "")
        out = self.decision(self.hook(project, "pre-bash", {"tool_name": "Bash", "tool_input": {"command": "fastlane release"}}))
        self.assertEqual(out["permissionDecision"], "ask")

    def test_garbage_input_does_not_crash(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=self.data, CLAUDE_PROJECT_DIR=project.root)
        for event in ("session-start", "pre-bash", "pre-edit", "post-edit", "stop"):
            proc = subprocess.run([sys.executable, fixtures.BIN, "hook", event], input=b"not json", stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            self.assertEqual(proc.returncode, 0, event + proc.stderr.decode())


class DoctorTests(unittest.TestCase):
    def run_doctor(self, project):
        from mobilekit import doctor
        lines = []
        code = doctor.main(project.root, out=lines.append)
        return code, "\n".join(lines)

    def test_reports_project_overlay_and_broad_rules(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write(".claude/settings.json", json.dumps({"permissions": {"allow": ["Bash(curl *)", "Bash(python3 -c *)", "Bash(xcodebuild *)"]}}))
        code, text = self.run_doctor(project)
        self.assertIn(code, (0, 1), text)
        self.assertIn("platforms: ios", text)
        self.assertIn("no AGENTS.md or CLAUDE.md", text)
        self.assertIn("2 allow rules that bypass guardrails", text)
        self.assertIn("no deny rules", text)
        self.assertIn("warnings", text)

    def test_adopted_project_has_clean_project_settings(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        adopt.main(project.root, marketplace="acme/mobile-coding-agents", out=lambda *_: None)
        _, text = self.run_doctor(project)
        self.assertIn("[ok] AGENTS.md", text)
        self.assertIn("[ok] .claude/settings.json:", text)
        self.assertNotIn(".claude/settings.json has", text)

    def test_plain_directory_is_not_an_error(self):
        project = fixtures.Project(git=False)
        self.addCleanup(project.cleanup)
        _, text = self.run_doctor(project)
        self.assertIn("no iOS, Android or Flutter project detected", text)


class AdoptTests(unittest.TestCase):
    def run_adopt(self, project, **kwargs):
        lines = []
        code = adopt.main(project.root, out=lines.append, **kwargs)
        return code, "\n".join(lines)

    def test_writes_the_overlay_for_the_detected_platform(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        code, text = self.run_adopt(project, marketplace="https://gitlab.com/acme/mobile-coding-agents.git")
        self.assertEqual(code, 0, text)
        for rel in ("AGENTS.md", "CLAUDE.md", ".mobile-coding-agents.json", ".claude/settings.json", ".claude/rules/mobile-ios.md"):
            self.assertTrue(project.exists(rel), rel)
        self.assertFalse(project.exists(".claude/rules/mobile-android.md"))
        self.assertFalse(project.exists(".claude/settings.local.json"))
        settings = json.loads(project.read(".claude/settings.json"))
        self.assertEqual(settings["enabledPlugins"], {"mobile-core@mobile-coding-agents": True, "mobile-ios@mobile-coding-agents": True})
        self.assertEqual(settings["extraKnownMarketplaces"]["mobile-coding-agents"]["source"], {"source": "git", "url": "https://gitlab.com/acme/mobile-coding-agents.git"})
        self.assertIn("Bash(xcodebuild *)", settings["permissions"]["allow"])
        self.assertIn("Read(.env)", settings["permissions"]["deny"])
        self.assertNotIn("Bash(./gradlew *)", settings["permissions"]["allow"])
        self.assertIn("iOS application.", project.read("AGENTS.md"))
        self.assertNotIn("{{", project.read("AGENTS.md") + project.read(".mobile-coding-agents.json"))
        self.assertTrue(project.read("CLAUDE.md").startswith("@AGENTS.md"))
        self.assertTrue(project.read(".claude/rules/mobile-ios.md").startswith("---\npaths:"))

    def test_local_marketplace_path_stays_out_of_shared_settings(self):
        project = fixtures.flutter_project(git=True)
        self.addCleanup(project.cleanup)
        code, text = self.run_adopt(project)
        self.assertEqual(code, 0, text)
        self.assertNotIn("extraKnownMarketplaces", json.loads(project.read(".claude/settings.json")))
        local = json.loads(project.read(".claude/settings.local.json"))
        self.assertEqual(local["extraKnownMarketplaces"]["mobile-coding-agents"]["source"]["source"], "directory")
        self.assertTrue(os.path.isfile(os.path.join(local["extraKnownMarketplaces"]["mobile-coding-agents"]["source"]["path"], ".claude-plugin", "marketplace.json")))

    def test_never_overwrites_and_is_repeatable(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("AGENTS.md", "# ours\n")
        project.write(".claude/settings.json", json.dumps({"permissions": {"allow": ["Bash(make *)"], "deny": []}, "model": "opus"}))
        code, text = self.run_adopt(project, marketplace="acme/mobile-coding-agents")
        self.assertEqual(code, 0, text)
        self.assertEqual(project.read("AGENTS.md"), "# ours\n")
        self.assertTrue(project.exists("AGENTS.md.proposed"))
        self.assertEqual(json.loads(project.read(".claude/settings.json"))["permissions"]["allow"], ["Bash(make *)"])
        self.assertTrue(project.exists(".claude/settings.json.proposed"))
        _, again = self.run_adopt(project, marketplace="acme/mobile-coding-agents")
        self.assertIn("same     CLAUDE.md", again)

    def test_merge_settings_only_adds_and_keeps_a_backup(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write(".claude/settings.json", json.dumps({"permissions": {"allow": ["Bash(make *)"]}, "model": "opus", "enabledPlugins": {"mobile-ios@mobile-coding-agents": False}}))
        code, text = self.run_adopt(project, marketplace="acme/mobile-coding-agents", merge_settings=True)
        self.assertEqual(code, 0, text)
        merged = json.loads(project.read(".claude/settings.json"))
        self.assertEqual(merged["model"], "opus")
        self.assertIn("Bash(make *)", merged["permissions"]["allow"])
        self.assertIn("Bash(xcodebuild *)", merged["permissions"]["allow"])
        self.assertIs(merged["enabledPlugins"]["mobile-ios@mobile-coding-agents"], False, "an explicit choice is kept")
        self.assertIs(merged["enabledPlugins"]["mobile-core@mobile-coding-agents"], True)
        self.assertEqual(merged["extraKnownMarketplaces"]["mobile-coding-agents"]["source"], {"source": "github", "repo": "acme/mobile-coding-agents"})
        self.assertEqual(len([n for n in os.listdir(os.path.join(project.root, ".claude")) if ".bak-" in n]), 1)

    def test_dry_run_writes_nothing_and_bad_targets_are_refused(self):
        project = fixtures.android_project(git=True)
        self.addCleanup(project.cleanup)
        code, text = self.run_adopt(project, dry_run=True)
        self.assertEqual(code, 0, text)
        self.assertIn("create   AGENTS.md", text)
        self.assertFalse(project.exists("AGENTS.md"))
        empty = fixtures.Project(git=False)
        self.addCleanup(empty.cleanup)
        self.assertEqual(self.run_adopt(empty)[0], 2)
        self.assertEqual(self.run_adopt(empty, platforms=["ios", "android", "flutter"], dry_run=True)[0], 0)
        self.assertEqual(self.run_adopt(empty, platforms=["windows"])[0], 2)
        self.assertEqual(adopt.main(adopt.marketplace_root(), out=lambda *_: None), 2)


if __name__ == "__main__":
    unittest.main()

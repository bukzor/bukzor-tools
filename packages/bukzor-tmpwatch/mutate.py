"""Inject each planned mutation, run the test that should catch it, restore.

Every entry names a way to break the code and the one test that must fail when
it is broken. A test nobody has watched fail is a test that proves nothing, and
most of these tests were written after the code they cover, so this is how they
earn their claim. Run it from anywhere:

    uv run python packages/bukzor-tmpwatch/mutate.py

It edits files in place and restores them in a finally block. If it is killed
mid-run, `git status` shows what is still mutated.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO = PKG.parents[1]
LIB = PKG / "lib/bukzor_tmpwatch"
T = "packages/bukzor-tmpwatch/lib/bukzor_tmpwatch"

MUTATIONS = [
    # --- settings are mandatory, never guessed ---
    (
        "missing files unnoticed",
        LIB / "config.py",
        "if not (directory / name).is_file()",
        "if False",
        f"{T}/config_test.py::DescribeMissingSettings::it_names_every_file_an_empty_directory_lacks",
    ),
    (
        "reader guesses a default",
        LIB / "config.py",
        "raise MissingSettings([path])",
        "return []",
        f"{T}/config_test.py::DescribeReadValues::it_refuses_a_setting_that_has_no_file",
    ),
    (
        "load ignores what is missing",
        LIB / "config.py",
        "if missing:",
        "if False:",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_refuses_to_guess_when_there_are_no_settings",
    ),
    (
        "unconfigured exits clean",
        LIB / "cli.py",
        "        return 2",
        "        return 0",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_refuses_to_guess_when_there_are_no_settings",
    ),
    (
        "hint forgets the installer",
        LIB / "cli.py",
        'print("run bukzor-tmpwatch-install to write the defaults", file=sys.stderr)',
        'print("configure it first", file=sys.stderr)',
        f"{T}/acceptance_test.py::DescribeTheCommand::it_refuses_to_guess_when_there_are_no_settings",
    ),
    (
        "every setting reported as gone",
        LIB / "config.py",
        "missing = missing_settings(directory)",
        "missing = [directory / name for name in setting_names()]",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_names_only_the_setting_that_is_gone",
    ),
    # --- the config format itself ---
    (
        "comments not stripped",
        LIB / "config.py",
        'line.split("#", 1)[0].strip()',
        "line.strip()",
        f"{T}/config_test.py::DescribeParseLines::it_reads_nothing_from_an_all_comment_file",
    ),
    (
        "emptied file not honored",
        LIB / "config.py",
        "return parse_lines(path.read_text())",
        "return parse_lines(path.read_text()) or [setting]",
        f"{T}/config_test.py::DescribeReadValues::it_takes_an_emptied_file_as_the_empty_list",
    ),
    (
        "setting name not kebabbed",
        LIB / "config.py",
        'path = directory / setting.replace("_", "-")',
        "path = directory / setting",
        f"{T}/config_test.py::DescribeReadValues::it_spells_a_setting_with_dashes",
    ),
    (
        "second value tolerated",
        LIB / "config.py",
        "assert len(values) <= 1, (setting, values)",
        "values = values[:1]",
        f"{T}/config_test.py::DescribeReadValue::it_refuses_a_second_value",
    ),
    (
        "days not validated",
        LIB / "config.py",
        "assert value.isdigit(), (setting, value)",
        "pass",
        f"{T}/config_test.py::DescribeReadDays::it_refuses_anything_that_is_not_one",
    ),
    (
        "tilde left unexpanded",
        LIB / "config.py",
        "Path(value).expanduser()",
        "Path(value)",
        f"{T}/config_test.py::DescribeLoadConfig::it_expands_a_tilde_in_a_root",
    ),
    (
        "empty quarantine allowed",
        LIB / "config.py",
        "assert self.quarantine_dir, self",
        "assert True, self",
        f"{T}/config_test.py::DescribeConfig::it_refuses_an_empty_quarantine_dir",
    ),
    (
        "boot read when unasked",
        LIB / "config.py",
        "if not any(BOOT in name for name in names):",
        "if False:",
        f"{T}/config_test.py::DescribeExpandKeep::it_does_not_read_a_boot_time_nobody_asked_for",
    ),
    # --- guards on what a setting may say ---
    (
        "quarantine dir may be a path",
        LIB / "config.py",
        "        assert Path(self.quarantine_dir).name == self.quarantine_dir, self",
        "        pass",
        f"{T}/config_test.py::DescribeConfigNames::it_refuses_a_quarantine_dir_that_is_a_path",
    ),
    (
        "trash dir may be a path",
        LIB / "config.py",
        "        assert not self.trash_dir or Path(self.trash_dir).name == self.trash_dir, self",
        "        pass",
        f"{T}/config_test.py::DescribeConfigNames::it_refuses_a_trash_dir_that_is_a_path",
    ),
    (
        "roots may be relative",
        LIB / "config.py",
        "        assert all(root.is_absolute() for root in self.roots), self",
        "        pass",
        f"{T}/config_test.py::DescribeConfigNames::it_refuses_a_relative_root",
    ),
    (
        "negative wait accepted",
        LIB / "cli.py",
        "    if not value.isdigit():",
        "    if False:",
        f"{T}/cli_test.py::DescribeParseArgs::it_refuses_a_negative_wait",
    ),
    (
        "zero wait rejected",
        LIB / "cli.py",
        "    if not value.isdigit():",
        "    if True:",
        f"{T}/cli_test.py::DescribeParseArgs::it_takes_a_wait_of_zero",
    ),
    # --- a name quarantined twice in one day ---
    (
        "collision clobbers",
        LIB / "sweep.py",
        "        name = free_name(batch, entry.name)",
        "        name = entry.name",
        f"{T}/sweep_test.py::DescribeProcQuarantine::it_keeps_both_when_a_name_is_quarantined_twice_in_a_day",
    ),
    (
        "collision unreported",
        LIB / "sweep.py",
        '        yield Change("quarantine", root, name)',
        '        yield Change("quarantine", root, entry.name)',
        f"{T}/sweep_test.py::DescribeProcQuarantine::it_names_the_collision_it_reports",
    ),
    (
        "dangling link looks free",
        LIB / "sweep.py",
        "    while (batch / candidate).exists() or (batch / candidate).is_symlink():",
        "    while (batch / candidate).exists():",
        f"{T}/sweep_test.py::DescribeFreeName::it_steps_over_a_dangling_symlink",
    ),
    # --- the shipped settings stay honest ---
    (
        "template hides a setting",
        LIB / "config.py",
        'return tuple(field.name.replace("_", "-") for field in fields(Config))',
        'return tuple(field.name.replace("_", "-") for field in fields(Config))[:-1]',
        f"{T}/config_test.py::DescribeTheTemplates::it_ships_one_per_setting",
    ),
    (
        "template drifts from the tests",
        LIB / "config.d/roots",
        "~/tmp",
        "~/scratch",
        f"{T}/config_test.py::DescribeTheTemplates::it_holds_the_defaults_every_test_here_assumes",
    ),
    (
        "shipped settings do not load",
        LIB / "config.d/quarantine-dir",
        "\nlost-and-found",
        "\n# lost-and-found",
        f"{T}/install_test.py::DescribeProcWriteSettings::it_writes_settings_the_command_can_load",
    ),
    # --- roots honor the config ---
    (
        "configured roots dropped",
        LIB / "roots.py",
        "            list(config.roots)\n            + [",
        "            [",
        f"{T}/roots_test.py::DescribeScratchRoots::it_starts_with_the_configured_roots",
    ),
    (
        "search name hardcoded",
        LIB / "roots.py",
        "find_dirs_named(home, config.trash_dir, config.prune)",
        'find_dirs_named(home, "trash", config.prune)',
        f"{T}/roots_test.py::DescribeScratchRoots::it_searches_for_the_configured_name",
    ),
    (
        "search cannot be disabled",
        LIB / "roots.py",
        "if not config.trash_dir:",
        "if False:",
        f"{T}/roots_test.py::DescribeScratchRoots::it_searches_at_all_only_when_a_name_is_configured",
    ),
    (
        "found name hardcoded",
        LIB / "roots.py",
        "yield here / name",
        'yield here / "trash"',
        f"{T}/roots_test.py::DescribeFindDirsNamed::it_looks_for_the_name_it_is_given",
    ),
    (
        "prune list hardcoded",
        LIB / "roots.py",
        "if child not in prune and not is_git_dir(here / child)",
        'if child not in ("node_modules",) and not is_git_dir(here / child)',
        f"{T}/roots_test.py::DescribeFindDirsNamed::it_descends_into_a_pruned_name_when_nothing_is_pruned",
    ),
    # --- roots nested in roots, and roots that vanish ---
    (
        "nested roots kept",
        LIB / "roots.py",
        "        if not any(other in root.parents for other in roots if other != root)",
        "        if True",
        f"{T}/roots_test.py::DescribeOutermost::it_drops_a_root_that_lies_inside_another",
    ),
    (
        "prefix mistaken for nesting",
        LIB / "roots.py",
        "if not any(other in root.parents for other in roots if other != root)",
        "if not any(str(root).startswith(str(other)) for other in roots if other != root)",
        f"{T}/roots_test.py::DescribeOutermost::it_keeps_a_root_that_only_shares_a_prefix",
    ),
    (
        "nesting not applied to discovery",
        LIB / "roots.py",
        "        return outermost(\n            list(config.roots)",
        "        return (\n            list(config.roots)",
        f"{T}/roots_test.py::DescribeScratchRoots::it_drops_a_trash_that_lies_inside_a_configured_root",
    ),
    (
        "vanished root crashes",
        LIB / "sweep.py",
        "    if not root.is_dir():\n        return\n",
        "",
        f"{T}/sweep_test.py::DescribeProcQuarantine::it_tolerates_a_root_that_has_gone_away",
    ),
    (
        "report collected before printing",
        LIB / "cli.py",
        "format_changes(remembering(changes, seen), config, today, dry_run)",
        "format_changes(remembering(list(changes), seen), config, today, dry_run)",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_reports_the_work_it_did_before_a_failure",
    ),
    # --- the sweep honors the config ---
    (
        "quarantine swept into itself",
        LIB / "sweep.py",
        "keep = config.keep | {config.quarantine_dir}",
        "keep = config.keep",
        f"{T}/sweep_test.py::DescribeProcQuarantine::it_never_quarantines_the_quarantine_itself",
    ),
    (
        "quarantine name hardcoded",
        LIB / "sweep.py",
        "batch = root / config.quarantine_dir / today.isoformat()",
        'batch = root / "lost-and-found" / today.isoformat()',
        f"{T}/sweep_test.py::DescribeProcQuarantine::it_honors_a_renamed_quarantine",
    ),
    (
        "kept names ignored",
        LIB / "sweep.py",
        "keep = config.keep | {config.quarantine_dir}",
        "keep = {config.quarantine_dir}",
        f"{T}/sweep_test.py::DescribeProcQuarantine::it_exempts_the_names_the_config_keeps",
    ),
    (
        "wait ignored",
        LIB / "sweep.py",
        "cutoff = now - config.quarantine_after_days * SECONDS_PER_DAY",
        "cutoff = now",
        f"{T}/sweep_test.py::DescribeProcQuarantine::it_waits_the_configured_number_of_days",
    ),
    (
        "purge wait ignored",
        LIB / "sweep.py",
        "cutoff = today - timedelta(days=config.purge_after_days)",
        "cutoff = today",
        f"{T}/sweep_test.py::DescribeProcPurge::it_keeps_a_batch_younger_than_the_purge_wait",
    ),
    # --- the report is grouped, not repeated ---
    (
        "header repeated per entry",
        LIB / "cli.py",
        "        if change.verb != verb:",
        "        if True:",
        f"{T}/cli_test.py::DescribeFormatChanges::it_states_the_action_and_root_once_each",
    ),
    (
        "root repeated per entry",
        LIB / "cli.py",
        "        if change.root != root:",
        "        if True:",
        f"{T}/cli_test.py::DescribeFormatChanges::it_states_the_action_and_root_once_each",
    ),
    (
        "root change unnoticed",
        LIB / "cli.py",
        "        if change.root != root:",
        "        if False:",
        f"{T}/cli_test.py::DescribeFormatChanges::it_repeats_the_root_only_when_it_changes",
    ),
    (
        "phases run together",
        LIB / "cli.py",
        "        if verb is not None:",
        "        if False:",
        f"{T}/cli_test.py::DescribeFormatChanges::it_separates_the_two_kinds_of_change",
    ),
    (
        "purge header says to",
        LIB / "cli.py",
        'return f"# {tense}, from {config.quarantine_dir}/"',
        'return f"# {tense}, to {config.quarantine_dir}/"',
        f"{T}/cli_test.py::DescribeHeader::it_names_the_directory_things_are_deleted_from",
    ),
    (
        "unknown verb tolerated",
        LIB / "cli.py",
        "        raise AssertionError(verb)",
        '        return ""',
        f"{T}/cli_test.py::DescribeHeader::it_refuses_a_verb_it_has_no_wording_for",
    ),
    (
        "report not grouped end to end",
        LIB / "cli.py",
        "format_changes(remembering(changes, seen), config, today, dry_run)",
        "(str(change) for change in remembering(changes, seen))",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_states_the_action_and_root_once_for_the_whole_list",
    ),
    (
        "broken pipe unhandled",
        LIB / "cli.py",
        "    signal.signal(signal.SIGPIPE, signal.SIG_DFL)",
        "    pass",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_tolerates_a_reader_that_stops_early",
    ),
    # --- the installer ---
    (
        "seeding overwrites answers",
        LIB / "install.py",
        "if not dest.exists():",
        "if True:",
        f"{T}/install_test.py::DescribeProcWriteSettings::it_never_overwrites_an_answer_already_given",
    ),
    (
        "seeds only one setting",
        LIB / "install.py",
        "for name in setting_names():",
        "for name in setting_names()[:1]:",
        f"{T}/install_test.py::DescribeProcWriteSettings::it_writes_a_template_for_every_setting",
    ),
    (
        "units copied, not linked",
        LIB / "install.py",
        "        dest.symlink_to(HERE / name)",
        "        shutil.copyfile(HERE / name, dest)",
        f"{T}/install_test.py::DescribeProcInstall::it_links_rather_than_copies",
    ),
    (
        "relink crashes on itself",
        LIB / "install.py",
        "        if dest.is_symlink() or dest.exists():",
        "        if False:",
        f"{T}/install_test.py::DescribeProcInstall::it_relinks_an_existing_link",
    ),
    (
        "hint overtakes the report",
        LIB / "cli.py",
        "        sys.stdout.flush()",
        "        pass",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_prints_the_hint_after_the_report_it_comments_on",
    ),
    # --- end to end ---
    (
        "config dir not consulted",
        LIB / "cli.py",
        "config = load_config(config_dir())",
        'config = load_config(Path("/nonexistent"))',
        f"{T}/acceptance_test.py::WhenConfigured::it_waits_the_number_of_days_a_setting_file_gives",
    ),
    (
        "flag cannot override",
        LIB / "cli.py",
        "if args.quarantine_after is not None:",
        "if False:",
        f"{T}/acceptance_test.py::WhenConfigured::it_lets_a_flag_override_a_setting_file",
    ),
    (
        "installer skips settings",
        LIB / "install.py",
        "proc_install(unit_dir()) + proc_write_settings(config_dir())",
        "proc_install(unit_dir())",
        f"{T}/acceptance_test.py::DescribeTheInstaller::it_seeds_every_setting_where_the_command_will_look",
    ),
    (
        "wheel drops templates",
        PKG / "pyproject.toml",
        'exclude = ["**/*_test.py"]',
        'exclude = ["**/*_test.py", "**/config.d/*"]',
        f"{T}/acceptance_test.py::DescribeTheWheel::it_ships_every_setting_template",
    ),
    (
        "wheel drops units",
        PKG / "pyproject.toml",
        'exclude = ["**/*_test.py"]',
        'exclude = ["**/*_test.py", "**/*.service"]',
        f"{T}/acceptance_test.py::DescribeTheWheel::it_ships_the_systemd_units",
    ),
    (
        "wheel ships tests",
        PKG / "pyproject.toml",
        'exclude = ["**/*_test.py"]',
        "exclude = []",
        f"{T}/acceptance_test.py::DescribeTheWheel::it_omits_the_tests",
    ),
    (
        "always write",
        LIB / "cli.py",
        "dry_run = not args.write",
        "dry_run = False",
        f"{T}/acceptance_test.py::DescribeTheCommand::it_reports_without_writing_by_default",
    ),
    (
        "hint while writing",
        LIB / "cli.py",
        "if seen and dry_run:",
        "if seen:",
        f"{T}/acceptance_test.py::WhenWriting::it_quarantines_into_a_batch_named_for_today",
    ),
    (
        "shallow mtime",
        LIB / "sweep.py",
        "    for dirpath, dirnames, filenames in os.walk(path):",
        "    for dirpath, dirnames, filenames in []:",
        f"{T}/acceptance_test.py::WhenWriting::it_leaves_an_entry_whose_contents_are_fresh",
    ),
    (
        "rendezvous ignored",
        LIB / "sweep.py",
        "and not is_rendezvous(entry)",
        "",
        f"{T}/acceptance_test.py::WhenWriting::it_never_sweeps_a_symlink",
    ),
    (
        "sockets swept",
        LIB / "sweep.py",
        "return stat.S_ISLNK(mode) or stat.S_ISSOCK(mode) or stat.S_ISFIFO(mode)",
        "return stat.S_ISLNK(mode)",
        f"{T}/sweep_test.py::DescribeIdleEntries::it_never_sweeps_a_socket",
    ),
    (
        "fifos swept",
        LIB / "sweep.py",
        "return stat.S_ISLNK(mode) or stat.S_ISSOCK(mode) or stat.S_ISFIFO(mode)",
        "return stat.S_ISLNK(mode) or stat.S_ISSOCK(mode)",
        f"{T}/sweep_test.py::DescribeIdleEntries::it_never_sweeps_a_fifo",
    ),
]


def main() -> int:
    stale = [
        (label, str(path))
        for label, path, old, _, _ in MUTATIONS
        if old not in path.read_text()
    ]
    assert not stale, stale

    # pytest exits 4 on a test id that names nothing, which reads here as a
    # non-zero return and so as a mutation caught. Every id must resolve, or
    # a typo would quietly report proof that was never obtained.
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", str(LIB), "-q", "--collect-only"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    ).stdout
    unknown = sorted({test for *_, test in MUTATIONS if test not in collected})
    assert not unknown, unknown

    gaps = 0
    for label, path, old, new, test in MUTATIONS:
        original = path.read_text()
        path.write_text(original.replace(old, new, 1))
        # A mutation that preserves file size is invisible to CPython's
        # (mtime, size) cache when it lands in the same second as the restore.
        for stale in LIB.rglob("__pycache__"):
            shutil.rmtree(stale)
        try:
            done = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    test,
                    "-q",
                    "-p",
                    "no:cacheprovider",
                ],
                capture_output=True,
                text=True,
                cwd=REPO,
                env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"},
            )
        finally:
            path.write_text(original)
        caught = done.returncode != 0
        gaps += not caught
        print(f"{'caught ' if caught else 'GAP    '} {label}")
    print(f"\n{len(MUTATIONS) - gaps}/{len(MUTATIONS)} caught")
    return gaps


if __name__ == "__main__":
    sys.exit(main())

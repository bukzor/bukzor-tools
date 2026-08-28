from pathlib import Path

import pytest

from .cli import parse_args


class DescribeParseArgs:
    def it_reports_without_writing_by_default(self):
        assert not parse_args([]).write

    def it_writes_only_when_asked(self):
        assert parse_args(["--write"]).write
        assert parse_args(["-w"]).write

    def it_refuses_the_flag_that_used_to_mean_dry_run(self):
        """A silently-accepted -n would read as a safeguard while writing."""
        with pytest.raises(SystemExit):
            parse_args(["-n"])

    def it_takes_roots_positionally(self):
        assert parse_args(["/x", "/y"]).root == [Path("/x"), Path("/y")]

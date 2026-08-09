from .watch import Sighting, acknowledged, add_url, read_urls, triage

EARLY = "2026-08-01T00:00:00Z"
LATE = "2026-08-09T19:21:28Z"
ISSUE = "https://github.com/rfjakob/earlyoom/issues/378"
OTHER = "https://issuetracker.google.com/issues/544148694"


class DescribeReadUrls:
    def it_drops_comments_and_blank_lines(self):
        text = f"# watched threads\n\n{ISSUE}  # the earlyoom one\n"
        assert read_urls(text) == [ISSUE]


class DescribeTriage:
    def it_seeds_urls_it_has_never_seen(self):
        result = triage({}, [Sighting(ISSUE, LATE)])
        assert result == ([Sighting(ISSUE, LATE)], [])

    def it_reports_activity_newer_than_the_acknowledged_mark(self):
        result = triage({ISSUE: EARLY}, [Sighting(ISSUE, LATE)])
        assert result == ([], [Sighting(ISSUE, LATE)])

    def it_stays_quiet_when_nothing_moved(self):
        assert triage({ISSUE: LATE}, [Sighting(ISSUE, LATE)]) == ([], [])


class DescribeAcknowledged:
    def it_records_both_seeded_and_newsworthy_sightings(self):
        state = acknowledged(
            {ISSUE: EARLY}, [Sighting(ISSUE, LATE), Sighting(OTHER, LATE)]
        )
        assert state == {ISSUE: LATE, OTHER: LATE}

    def it_keeps_acks_for_threads_this_batch_left_out(self):
        """--rc runs acknowledge only seeded threads; the rest must survive."""
        assert acknowledged({OTHER: EARLY}, [Sighting(ISSUE, LATE)]) == {
            OTHER: EARLY,
            ISSUE: LATE,
        }

    def it_leaves_the_input_state_alone(self):
        state = {ISSUE: EARLY}
        _ = acknowledged(state, [Sighting(ISSUE, LATE)])
        assert state == {ISSUE: EARLY}


class DescribeAddUrl:
    def it_appends_a_url_to_the_config(self):
        assert (
            add_url(f"# threads\n{ISSUE}\n", OTHER) == f"# threads\n{ISSUE}\n{OTHER}\n"
        )

    def it_is_idempotent(self):
        text = f"{ISSUE}\n"
        assert add_url(text, ISSUE) == text

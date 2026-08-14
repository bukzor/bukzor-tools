from .cli import format_news
from .watch import Sighting

ISSUE = "https://github.com/rfjakob/earlyoom/issues/378"
OTHER = "https://issuetracker.google.com/issues/544148694"
EARLY = "2026-08-01T00:00:00Z"
LATE = "2026-08-09T19:21:28Z"


class DescribeFormatNews:
    def it_is_empty_when_nothing_is_new(self):
        assert format_news([], {}, rc_mode=False) == ""

    def it_lists_one_line_per_thread(self):
        news = [Sighting(ISSUE, LATE), Sighting(OTHER, LATE)]
        state = {ISSUE: EARLY, OTHER: EARLY}
        text = format_news(news, state, rc_mode=False)
        assert f"UPSTREAM REPLY? {ISSUE} -- activity {LATE}, acked {EARLY}" in text
        assert f"UPSTREAM REPLY? {OTHER} -- activity {LATE}, acked {EARLY}" in text

    def it_ends_with_a_blank_line_to_keep_the_next_prompt_clear(self):
        text = format_news([Sighting(ISSUE, LATE)], {ISSUE: EARLY}, rc_mode=False)
        assert text.endswith("\n\n")

    def it_tells_rc_mode_readers_how_to_acknowledge(self):
        text = format_news([Sighting(ISSUE, LATE)], {ISSUE: EARLY}, rc_mode=True)
        assert "upstream-replies" in text.splitlines()[-2]

    def it_omits_the_ack_hint_outside_rc_mode(self):
        text = format_news([Sighting(ISSUE, LATE)], {ISSUE: EARLY}, rc_mode=False)
        assert "upstream-replies" not in text

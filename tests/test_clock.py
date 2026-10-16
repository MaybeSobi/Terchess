from terchess.clock import ChessClock, format_clock


def test_clock_counts_down_and_adds_increment():
    now = [100.0]
    clock = ChessClock(10, 2, now=lambda: now[0])
    clock.start(True)
    now[0] += 3.5
    assert clock.remaining(True) == 6.5
    assert clock.finish_move(True) is True
    assert clock.remaining(True) == 8.5
    assert clock.running_color is None


def test_clock_flags_when_no_time_remains():
    now = [0.0]
    clock = ChessClock(2, 1, now=lambda: now[0])
    clock.start(False)
    now[0] = 2.1
    assert clock.is_flagged(False)
    assert clock.finish_move(False) is False
    assert clock.remaining(False) == 0


def test_clock_cannot_start_other_side_while_running():
    clock = ChessClock(20, now=lambda: 0.0)
    clock.start(True)
    try:
        clock.start(False)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected a RuntimeError")


def test_format_clock():
    assert format_clock(65) == "1:05"
    assert format_clock(3601) == "1:00:01"
    assert format_clock(0) == "0:00"

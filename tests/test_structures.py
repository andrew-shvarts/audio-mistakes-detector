from src.structures import ErrorType, FileError


def test_file_error_to_dict_rounds_interval():
    error = FileError(ErrorType.MISSING, (1.23456, 2.0001), correction="hello")
    assert error.to_dict() == {
        "type": "missing",
        "start": 1.235,
        "end": 2.0,
        "correction": "hello",
    }


def test_file_error_str_includes_correction_when_present():
    error = FileError(ErrorType.FACTUAL, (0.0, 1.0), correction="fix me")
    assert "fix me" in str(error)


def test_file_error_str_omits_correction_when_absent():
    error = FileError(ErrorType.DUPLICATE, (0.0, 1.0))
    assert "->" not in str(error)


def test_file_error_instances_do_not_share_state():
    """Regression test: FileError previously had no isolation issues, but
    ErrorDetector.errors used to be a shared class-level list. This test
    documents the expected per-instance behavior at the FileError level."""
    e1 = FileError(ErrorType.MISSING, (0.0, 1.0))
    e2 = FileError(ErrorType.DUPLICATE, (2.0, 3.0))
    assert e1.error_type != e2.error_type
    assert e1.interval != e2.interval

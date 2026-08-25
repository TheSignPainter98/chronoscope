import pytest
from chronoscope.parser import text_parser

def test_parser_file_not_found():
    with pytest.raises(FileNotFoundError):
        _ = text_parser("")

def test_parser():
    line = """
    libuv[3433]: 2055-11-29T20:57:56.489282133 conn pid: 111 sm_id: 1 started |
    """
    _ = text_parser("test/chronoscope.yaml").parse([line])

def test_parser_malformed():
    line = """
    libuv[3433]: 2055-11-29T20:57:56.667095559 conn
    """
    _ = text_parser("test/chronoscope.yaml", verbose=True).parse([line])

def test_parser_fuzz():
    line = """
a b c d
    """
    _ = text_parser("test/chronoscope.yaml").parse([line])

def test_parser_empty():
    line = ""
    _ = text_parser("test/chronoscope.yaml").parse([line])

def test_parser_noise_silent_even_in_verbose(capsys):
    noise = ["", "   ", "a b c d", "libuv[3433]: conn"]
    records = text_parser("test/chronoscope.yaml",
                          verbose=True).parse(noise)
    assert all(not v for v in records.values())
    assert capsys.readouterr().err == ""

import pytest

from agent.cli import panel_urls, parse_args


def test_default_listens_on_localhost_8765():
    options = parse_args([])

    assert (options.host, options.port) == ("127.0.0.1", 8765)


def test_lan_listens_on_all_interfaces():
    assert parse_args(["--lan"]).host == "0.0.0.0"


def test_custom_port():
    assert parse_args(["--port", "9000"]).port == 9000


@pytest.mark.parametrize("argv", [["--port", "0"], ["--port", "70000"], ["--port", "abc"], ["--inconnu"]])
def test_invalid_arguments_exit(argv):
    with pytest.raises(SystemExit):
        parse_args(argv)


def test_local_url_carries_the_token():
    assert panel_urls("127.0.0.1", 8765, "TOK", lan_ips=["192.168.1.20"]) == ["http://127.0.0.1:8765/?token=TOK"]


def test_lan_urls_list_each_address():
    assert panel_urls("0.0.0.0", 8765, "TOK", lan_ips=["192.168.1.20", "10.0.0.5"]) == [
        "http://192.168.1.20:8765/?token=TOK",
        "http://10.0.0.5:8765/?token=TOK",
    ]


def test_lan_without_detected_address_falls_back_to_localhost():
    assert panel_urls("0.0.0.0", 8765, "TOK", lan_ips=[]) == ["http://127.0.0.1:8765/?token=TOK"]

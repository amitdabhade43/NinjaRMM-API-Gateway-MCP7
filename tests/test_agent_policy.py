from ninjaone_agent.agent import _method_for_tool


def test_call_method_detection():
    assert _method_for_tool("call", {"endpoint": "GET /v2/devices"}) == "GET"
    assert _method_for_tool("call", {"endpoint": "post /v2/device"}) == "POST"
    assert _method_for_tool("ninjaone__call", {"endpoint": "PATCH /v2/device/1"}) == "PATCH"


def test_raw_call_method_detection():
    assert _method_for_tool("raw_call", {"request": "DELETE /v2/device/1"}) == "DELETE"
    assert _method_for_tool("raw_call", {"request": "GET /v2/devices?page=2"}) == "GET"


def test_non_execution_tools_have_no_http_method():
    assert _method_for_tool("find_endpoint", {"query": "devices"}) is None
    assert _method_for_tool("describe_endpoint", {"endpoint": "GET /v2/devices"}) is None

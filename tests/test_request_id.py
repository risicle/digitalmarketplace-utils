from flask import request
from itertools import chain, product
import mock
import pytest

from dmutils.request_id import init_app as request_id_init_app


_trace_id_related_params = (
    (
        # extra_config
        {
            "DM_REQUEST_ID_HEADER": "DM-REQUEST-ID",
            "DM_DOWNSTREAM_REQUEST_ID_HEADER": "DOWNSTREAM-REQUEST-ID",
        },
        # extra_req_headers
        (
            ("DM-REQUEST-ID", "from-header",),
            ("DOWNSTREAM-REQUEST-ID", "from-downstream",),
        ),
        # expected_trace_id
        "from-header",
        # expect_uuid_call
        False,
        # expected_onwards_req_headers
        {
            "DM-REQUEST-ID": "from-header",
            "DOWNSTREAM-REQUEST-ID": "from-header",
        },
    ),
    (
        {
            "DM_REQUEST_ID_HEADER": "DM-REQUEST-ID",
            "DM_DOWNSTREAM_REQUEST_ID_HEADER": "DOWNSTREAM-REQUEST-ID",
        },
        (
            ("DOWNSTREAM-REQUEST-ID", "from-downstream",),
        ),
        "from-downstream",
        False,
        {
            "DM-REQUEST-ID": "from-downstream",
            "DOWNSTREAM-REQUEST-ID": "from-downstream",
        },
    ),
    (
        {
            "DM_REQUEST_ID_HEADER": "DM-REQUEST-ID",
            "DM_DOWNSTREAM_REQUEST_ID_HEADER": "",
        },
        (),
        "generated",
        True,
        {
            "DM-REQUEST-ID": "generated",
            "X-B3-TraceId": "generated",
        },
    ),
    (
        {
            "DM_REQUEST_ID_HEADER": "DM-REQUEST-ID",
            "DM_DOWNSTREAM_REQUEST_ID_HEADER": "DOWNSTREAM-REQUEST-ID",
        },
        (),
        "generated",
        True,
        {
            "DM-REQUEST-ID": "generated",
            "DOWNSTREAM-REQUEST-ID": "generated",
        },
    ),
    (
        {
            "DM_REQUEST_ID_HEADER": "DM-REQUEST-ID",
            "DM_DOWNSTREAM_REQUEST_ID_HEADER": "DOWNSTREAM-REQUEST-ID",
        },
        (),
        "generated",
        True,
        {
            "DM-REQUEST-ID": "generated",
            "DOWNSTREAM-REQUEST-ID": "generated",
        },
    ),
    (
        {
            "DM_TRACE_ID_HEADERS": ("x-tommy-caffrey", "y-jacky-caffrey",),
            "DM_REQUEST_ID_HEADER": "DM-REQUEST-ID",
            "DM_DOWNSTREAM_REQUEST_ID_HEADER": "DOWNSTREAM-REQUEST-ID",
        },
        (
            # these should both be ignored because of the presence of the DM_TRACE_ID_HEADERS setting
            ("DM-REQUEST-ID", "from-header",),
            ("DOWNSTREAM-REQUEST-ID", "from-downstream",),
        ),
        "generated",
        True,
        {
            "x-tommy-caffrey": "generated",
            "y-jacky-caffrey": "generated",
        },
    ),
    (
        {
            "DM_TRACE_ID_HEADERS": ("x-tommy-caffrey", "y-jacky-caffrey",),
        },
        (
            ("y-jacky-caffrey", "jacky-header-value",),
            ("x-tommy-caffrey", "tommy-header-value",),
        ),
        "tommy-header-value",
        False,
        {
            "x-tommy-caffrey": "tommy-header-value",
            "y-jacky-caffrey": "tommy-header-value",
        },
    ),
    (
        {
            "DM_REQUEST_ID_HEADER": "DM-REQUEST-ID",
            # not setting DM_DOWNSTREAM_REQUEST_ID_HEADER should cause it to fall back to the default, X-B3-TraceId
        },
        (
            ("x-kidneys", "pork",),
            ("x-b3-traceid", "Grilled Mutton",),
        ),
        "Grilled Mutton",
        False,
        {
            "DM-REQUEST-ID": "Grilled Mutton",
            "X-B3-TraceId": "Grilled Mutton",
        },
    ),
)


_span_id_related_params = (
    (
        # extra_config
        {},
        # extra_req_headers
        (
            ("x-b3-spanid", "Steak, kidney, liver, mashed",),
        ),
        # expected_span_id
        "Steak, kidney, liver, mashed",
        # expected_onwards_req_headers
        {
            "X-B3-SpanId": "Steak, kidney, liver, mashed",
        },
    ),
    (
        {},
        (),
        None,
        {},
    ),
    (
        {
            "DM_SPAN_ID_HEADERS": ("barrels-and-boxes", "Bloomusalem",),
        },
        (
            ("bloomusalem", "huge-pork-kidney",),
        ),
        "huge-pork-kidney",
        {
            "barrels-and-boxes": "huge-pork-kidney",
            "Bloomusalem": "huge-pork-kidney",
        },
    ),
)


_parent_span_id_related_params = (
    (
        # extra_config
        {},
        # extra_req_headers
        (
            ("X-B3-PARENTSPAN", "colossal-edifice",),
            ("X-WANDERING-SOAP", "Flower of the Bath",),
        ),
        # expected_parent_span_id
        "colossal-edifice",
    ),
    (
        {},
        (),
        None,
    ),
    (
        {
            "DM_PARENT_SPAN_ID_HEADERS": ("Potato-Preservative",),
        },
        (
            ("POTATO-PRESERVATIVE", "Plage and Pestilence",),
        ),
        "Plage and Pestilence",
    ),
)


@pytest.mark.parametrize(
    ",".join((
        "extra_config",
        "extra_req_headers",
        "expected_trace_id",
        "expect_uuid_call",
        "expected_span_id",
        "expected_parent_span_id",
        "expected_onwards_req_headers",
    )), tuple(
    # to prove that the behaviour of trace_id, span_id and parent_span_id is independent, we use the cartesian product
    # of all sets of parameters to test every possible combination of scenarios we've provided...
    (
        # extra_config
        {**t_extra_config, **s_extra_config, **p_extra_config},
        # extra_req_headers
        tuple(chain(t_extra_req_headers, s_extra_req_headers, p_extra_req_headers)),
        expected_trace_id,
        expect_uuid_call,
        expected_span_id,
        expected_parent_span_id,
        # expected_onwards_req_headers
        {**t_expected_onwards_req_headers, **s_expected_onwards_req_headers},
    ) for (
        t_extra_config,
        t_extra_req_headers,
        expected_trace_id,
        expect_uuid_call,
        t_expected_onwards_req_headers,
    ), (
        s_extra_config,
        s_extra_req_headers,
        expected_span_id,
        s_expected_onwards_req_headers,
    ), (
        p_extra_config,
        p_extra_req_headers,
        expected_parent_span_id,
    ) in product(_trace_id_related_params, _span_id_related_params, _parent_span_id_related_params)
))
@mock.patch('dmutils.request_id.uuid.uuid4', autospec=True)
def test_request_header(
    uuid4_mock,
    app,
    extra_config,
    extra_req_headers,
    expected_trace_id,
    expect_uuid_call,
    expected_span_id,
    expected_parent_span_id,
    expected_onwards_req_headers,
):
    app.config.update(extra_config)
    request_id_init_app(app)

    uuid4_mock.return_value = "generated"

    with app.test_request_context(headers=extra_req_headers):
        assert request.request_id == request.trace_id == expected_trace_id
        assert request.span_id == expected_span_id
        assert request.parent_span_id == expected_parent_span_id
        assert request.get_onwards_request_headers() == expected_onwards_req_headers

    assert uuid4_mock.called is expect_uuid_call


def test_request_id_is_set_on_response(app):
    request_id_init_app(app)
    client = app.test_client()

    with app.app_context():
        response = client.get('/', headers={'DM-REQUEST-ID': 'generated'})
        assert response.headers['DM-Request-ID'] == 'generated'


def test_request_id_is_set_on_error_response(app):
    request_id_init_app(app)
    client = app.test_client()

    @app.route('/')
    def error_route():
        raise Exception()

    with app.app_context():
        response = client.get('/', headers={'DM-REQUEST-ID': 'generated'})
        assert response.status_code == 500
        assert response.headers['DM-Request-ID'] == 'generated'

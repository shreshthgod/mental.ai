"""Header contract only: no keys or requests to a real Supabase project."""
from api.db import SupabaseClient, Response


def test_non_jwt_keys_are_not_sent_as_bearer_tokens():
    observed = []
    def transport(method, url, headers, body, timeout):
        observed.append(dict(headers))
        return Response(200, {}, b'[]')
    client = SupabaseClient('https://synthetic.invalid', 'sb_publishable_synthetic', 'sb_secret_synthetic', transport=transport)
    client._call('POST', '/auth/v1/token', privileged=False)
    client._call('GET', '/rest/v1/screenings', privileged=True)
    assert observed[0]['apikey'] == 'sb_publishable_synthetic'
    assert observed[1]['apikey'] == 'sb_secret_synthetic'
    assert all('Authorization' not in headers for headers in observed)


def test_verified_user_bearer_is_separate_from_new_application_key():
    observed = []
    def transport(method, url, headers, body, timeout):
        observed.append(dict(headers))
        return Response(200, {}, b'[]')
    client = SupabaseClient('https://synthetic.invalid', 'sb_publishable_synthetic', 'sb_secret_synthetic', transport=transport)
    for user in ('synthetic-user-a', 'synthetic-user-b'):
        client._call('GET', '/auth/v1/user', privileged=False, access_token=user)
    assert [r['Authorization'] for r in observed] == ['Bearer synthetic-user-a', 'Bearer synthetic-user-b']
    assert all(r['apikey'] == 'sb_publishable_synthetic' for r in observed)


def test_legacy_key_bearer_compatibility_is_retained():
    client = SupabaseClient('https://synthetic.invalid', 'synthetic.anon.jwt', 'synthetic.service.jwt')
    assert client._headers(privileged=False)['Authorization'] == 'Bearer synthetic.anon.jwt'
    assert client._headers(privileged=True)['Authorization'] == 'Bearer synthetic.service.jwt'

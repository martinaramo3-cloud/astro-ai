"""Security regressions use synthetic accounts and never call external services."""
import io
from concurrent.futures import ThreadPoolExecutor
import threading
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from PIL import Image
from tests.conftest import SOFIA
from app.database import get_db_connection, init_db
from app.chat_service import summarize_recent_sessions
from app.auth_token_service import issue_token, consume_token, PURPOSE_RESET
from app.security_service import rate_limit
import app.ai_service as ai


def test_profile_ownership_on_chat_create_update_and_legacy_join(client, account):
    victim, vh = account('victim@example.com')
    attacker, ah = account('attacker@example.com')
    p = client.post('/profiles', headers=vh, json={'owner_user_id':victim['id'],'label':'Private label','person_name':'Test',**SOFIA}).json()
    data={'owner_user_id':attacker['id'],'profile_id':p['id'],'title':'test','messages':[]}
    assert client.post('/chat-sessions',headers=ah,json=data).status_code == 403
    own=client.post('/chat-sessions',headers=ah,json={**data,'profile_id':None}).json()
    assert client.patch('/chat-sessions/'+str(own['id']),headers=ah,json=data).status_code == 403
    conn=get_db_connection()
    conn.execute('UPDATE chat_sessions SET profile_id=? WHERE id=?',(p['id'],own['id']))
    conn.commit(); conn.close()
    assert summarize_recent_sessions(attacker['id'])[0]['about'] == 'themselves'
    init_db()
    assert client.get('/chat-sessions/session/'+str(own['id']),headers=ah).json()['profile_id'] is None


def test_bad_invite_place_does_not_spend_link(client,account):
    _,h=account()
    token=client.post('/invites',headers=h,json={'label':'Friend'}).json()['token']
    data={**SOFIA,'person_name':'Test','birth_place':'invalid'}
    assert client.post('/invite/'+token,json=data).status_code == 400
    assert client.post('/invite/'+token,json={**data,'birth_place':SOFIA['birth_place']}).status_code == 200
    assert client.post('/invite/'+token,json={**data,'birth_place':SOFIA['birth_place']}).status_code == 404


def test_full_slot_keeps_invite_usable(client,account):
    user,h=account()
    token=client.post('/invites',headers=h,json={'label':'Friend'}).json()['token']
    p=client.post('/profiles',headers=h,json={'owner_user_id':user['id'],'label':'Friend','person_name':'Test',**SOFIA}).json()
    assert client.post('/invite/'+token,json={**SOFIA,'person_name':'Test'}).status_code == 402
    assert client.get('/invite/'+token).status_code == 200
    client.delete('/profiles/'+str(p['id']),headers=h)
    assert client.post('/invite/'+token,json={**SOFIA,'person_name':'Test'}).status_code == 200


def test_concurrent_invite_creates_one_person(account):
    from app.invite_service import create_invite, accept_invite
    user,_=account()
    token=create_invite(user['id'],'Friend')
    barrier=threading.Barrier(2)
    def fill(_):
        barrier.wait(timeout=5)
        try:
            accept_invite(token,{**SOFIA,'person_name':'Test','birth_time_known':True})
            return 200
        except HTTPException as e:
            return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(fill,range(2))) == [200,404]


def test_account_deletion_cleans_all_linked_records(client,account):
    from app.invite_service import create_invite
    from app.usage_log_service import log_usage
    user,h=account()
    issue_token(user['id'],PURPOSE_RESET)
    create_invite(user['id'],'Private label','Private name')
    log_usage(user['id'],'gpt-4.1-mini',100,100)
    client.post('/bug-reports',headers=h,json={'message':'Private report'})
    assert client.delete('/me',headers=h).status_code == 200
    conn=get_db_connection()
    for table,col in [('auth_tokens','user_id'),('invites','owner_user_id'),('bug_reports','user_id'),('usage_events','user_id'),('sessions','user_id')]:
        assert conn.execute(f'SELECT count(*) FROM {table} WHERE {col}=?',(user['id'],)).fetchone()[0] == 0
    conn.close()


def test_rate_limits_logins_and_email_cooldown(client,account,monkeypatch):
    import app.main as main
    account()
    emails=[]
    monkeypatch.setattr(main,'send_password_reset',lambda *a,**kw:emails.append(a))
    for _ in range(10):
        assert client.post('/login',json={'email':'her@example.com','password':'wrong'}).status_code == 401
    blocked=client.post('/login',json={'email':'her@example.com','password':'wrong'})
    assert blocked.status_code == 429 and int(blocked.headers['Retry-After']) > 0
    assert client.post('/forgot-password',json={'email':'her@example.com'}).status_code == 200
    assert client.post('/forgot-password',json={'email':'HER@example.com'}).status_code == 429
    assert len(emails) == 1


def test_rate_limit_atomic_and_expires(monkeypatch):
    import app.security_service as security
    clock=[100.0]
    monkeypatch.setattr(security.time,'time',lambda:clock[0])
    def hit(_):
        try: rate_limit('test','same',1,60); return 200
        except HTTPException as e: return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(hit,range(2))) == [200,429]
    clock[0]=161.0
    assert hit(0) == 200


@pytest.mark.parametrize('field,value',[('birth_date','not-a-date'),('birth_date','2999-01-01'),('birth_time','99:99'),('email','bad email'),('name','x'*301)])
def test_invalid_signup_rejected_before_save(client,field,value):
    payload={'name':'Test','email':'test@example.com','password':'Moonlight9!',**SOFIA,field:value}
    assert client.post('/signup',json=payload).status_code == 422
    conn=get_db_connection(); assert conn.execute('SELECT count(*) FROM users').fetchone()[0] == 0; conn.close()


def test_html_email_escapes_names(monkeypatch):
    import app.email_service as email
    sent=[]
    monkeypatch.setattr(email,'_send',lambda to,subject,html:sent.append(html))
    name='<a href="https://example.invalid">Injected</a>'
    for send in (email.send_verification,email.send_password_reset):
        send('test@example.com',name,'https://example.invalid/verify')
    assert all(name not in html and '&lt;a href=' in html for html in sent)


def test_reset_token_atomic_even_when_both_read_unused(account,monkeypatch):
    import app.auth_token_service as auth
    user,_=account(); token=issue_token(user['id'],PURPOSE_RESET)
    original=auth.get_db_connection; barrier=threading.Barrier(2)
    class Cursor:
        def __init__(self,c): self.c=c
        def fetchone(self):
            row=self.c.fetchone(); barrier.wait(timeout=5); return row
    class Conn:
        def __init__(self): self.conn=original()
        def execute(self,q,*args):
            r=self.conn.execute(q,*args)
            return Cursor(r) if q.startswith('SELECT id, user_id') else r
        def commit(self): self.conn.commit()
        def close(self): self.conn.close()
    monkeypatch.setattr(auth,'get_db_connection',Conn)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:consume_token(token,PURPOSE_RESET),range(2)))
    assert results.count(user['id']) == 1 and results.count(None) == 1




def test_claude_stream_and_regular_forward_output_cap(monkeypatch,account):
    user,_=account()
    conn=get_db_connection(); conn.execute('UPDATE users SET email_verified=1 WHERE id=?',(user['id'],)); conn.commit(); conn.close()
    seen=[]
    class Stream:
        text_stream=['Hello']
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def get_final_message(self):
            return SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='Hello')],usage=SimpleNamespace(input_tokens=10,output_tokens=10))
    def stream(**kw): seen.append(kw['max_tokens']); return Stream()
    monkeypatch.setattr(ai,'_get_anthropic_client',lambda:SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream))))
    assert ai.generate_astrologer_answer('hello',model='claude-sonnet-5',user_id=user['id'],max_output_tokens=180)[0] == 'Hello'
    assert list(ai.stream_astrologer_answer('hello',model='claude-sonnet-5',user_id=user['id'],max_output_tokens=240)) == ['Hello']
    assert seen == [180,240]


def test_large_body_and_private_health(client):
    r=client.post('/login',content=b'x'*(256*1024+1),headers={'Content-Type':'application/json'})
    assert r.status_code == 413
    assert client.get('/health').json() == {'status':'ok'}
    assert client.get('/admin/health').status_code == 401
    assert client.get('/health').headers['X-Content-Type-Options'] == 'nosniff'


def test_upload_validates_bytes_and_storage_quota(account):
    from app.attachment_service import save_attachment, get_attachment, delete_attachment
    user,_=account()
    with pytest.raises(HTTPException) as exc: save_attachment(user['id'],b'<script>bad</script>','image/png')
    assert exc.value.status_code == 400
    buffer=io.BytesIO(); Image.new('RGB',(2,2)).save(buffer,format='PNG')
    saved=save_attachment(user['id'],buffer.getvalue(),'image/png')
    assert get_attachment(saved['id']) is not None
    conn=get_db_connection(); conn.execute('UPDATE attachments SET byte_size=? WHERE id=?',(50*1024*1024,saved['id'])); conn.commit(); conn.close()
    with pytest.raises(HTTPException) as exc: save_attachment(user['id'],buffer.getvalue(),'image/png')
    assert exc.value.status_code == 413
    assert delete_attachment(saved['id'],user['id'])


def test_reset_revokes_old_sessions_and_only_changes_password_once(client,account):
    user,h=account()
    token=issue_token(user['id'],PURPOSE_RESET)
    response=client.post('/reset-password',json={'token':token,'password':'UpdatedPass42!'})
    assert response.status_code == 200
    assert client.get('/me',headers=h).status_code == 401
    assert client.post('/reset-password',json={'token':token,'password':'OtherPass42!'}).status_code == 400
    assert client.post('/login',json={'email':user['email'],'password':'UpdatedPass42!'}).status_code == 200


def test_invite_failure_rolls_back_token(account):
    from app.invite_service import create_invite, accept_invite, peek_invite
    import sqlite3
    user,_=account(); token=create_invite(user['id'],'Friend')
    conn=get_db_connection()
    conn.execute("CREATE TRIGGER test_block_profile BEFORE INSERT ON profiles BEGIN SELECT RAISE(ABORT,'test failure'); END")
    conn.commit(); conn.close()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            accept_invite(token,{**SOFIA,'person_name':'Test','birth_time_known':True})
        assert peek_invite(token) is not None
    finally:
        conn=get_db_connection(); conn.execute('DROP TRIGGER test_block_profile'); conn.commit(); conn.close()


def test_late_usage_after_account_deletion_stays_anonymous(client,account):
    from app.usage_log_service import log_usage
    user,h=account(); client.delete('/me',headers=h)
    assert log_usage(user['id'],'gpt-4.1-mini',10,10)
    conn=get_db_connection(); assert conn.execute('SELECT user_id FROM usage_events').fetchone()[0] is None; conn.close()

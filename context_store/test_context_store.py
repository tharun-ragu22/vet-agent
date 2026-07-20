from context_store import ContextStore, ConversationTurn
def test_context_store_nonexistant_id_gets_nothing():
    store = ContextStore()
    context = store.get_context(call_sid='1234')
    assert len(context) == 0

def test_context_store_existing_id_should_get_result():
    store = ContextStore()
    store.add_message(call_sid = '1234', role = 'user', content = 'hi there')
    
    context = store.get_context(call_sid='1234')
    assert len(context) == 1

    msg = context[0]
    assert msg.role == 'user'
    assert msg.content == 'hi there'
from context_store import ContextStore
def test_context_store_nonexistant_id_gets_nothing():
    store = ContextStore()
    context = store.get_context(call_sid='1234')
    assert len(context) == 0
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=str(Path(__file__).resolve().parents[1]/'app.py')

def test_app_initial_render_has_question_and_history_controls():
    at=AppTest.from_file(APP,default_timeout=20).run()
    assert not at.exception
    assert len(at.chat_input)==1
    assert any(b.label=='清空对话' for b in at.button)

def test_app_missing_configuration_is_explained_without_secrets(monkeypatch):
    from school_agent.config import Settings
    monkeypatch.setattr(Settings,'load',classmethod(lambda cls: Settings(database_url='')))
    at=AppTest.from_file(APP,default_timeout=20).run()
    assert not at.exception
    assert any('DATABASE_URL' in e.value for e in at.error)

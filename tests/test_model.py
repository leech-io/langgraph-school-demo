import pytest
from school_agent.model import parse_plan

def test_accepts_json_or_fenced_json():
    assert parse_plan('```json\n{"queries":["SELECT score FROM student_grades"]}\n```').queries==['SELECT score FROM student_grades']

def test_rejects_explanatory_text_and_empty_plan():
    for text in ['I think SELECT', '{"queries":[]}', '{"queries":[1]}']:
        with pytest.raises(ValueError):parse_plan(text)

def test_model_initializes_with_socks_environment_without_optional_dependency(monkeypatch):
    from school_agent.model import SchoolModel
    from school_agent.config import Settings
    monkeypatch.setenv('ALL_PROXY','socks5://127.0.0.1:9999')
    for key in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy'):monkeypatch.delenv(key,raising=False)
    model=SchoolModel(Settings(model_api_key='test-local-only'))
    assert model.llm is not None

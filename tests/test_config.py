from school_agent.config import Settings, redact

def test_redacts_password_key_and_url():
    settings=Settings(database_url='mysql+pymysql://ro:private-password@localhost/school_demo',model_api_key='private-key')
    s=redact('private-password private-key mysql+pymysql://ro:private-password@localhost/school_demo',settings)
    assert 'private-password' not in s and 'private-key' not in s and 'mysql+pymysql://' not in s

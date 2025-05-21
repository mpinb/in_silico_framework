import pytest

@pytest.fixture(scope="session", autouse=True)
def compile_mechanisms_once():
    """Trigger compilation of mechanisms once per session.
    
    Simply importing mechanisms triggers a compilation.
    It's important to scope this trigger to the session level to avoid recompilation
    or race conditions when running tests in parallel.
    """ 
    import mechanisms.l5pt
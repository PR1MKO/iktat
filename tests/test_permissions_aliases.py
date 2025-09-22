from app.utils.permissions import capabilities_for


class DummyUser:
    def __init__(self, role: str):
        self.role = role


def test_capabilities_for_szig_alias_allows_assignment(app):
    caps = capabilities_for(DummyUser("szig"))
    assert caps.get("can_assign") is True

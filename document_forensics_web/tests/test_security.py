from app.security import safe_filename, sha256_bytes


def test_safe_filename_removes_path_traversal():
    assert safe_filename("../../relatorio (1).docx") == "relatorio (1).docx"


def test_hash_is_stable():
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

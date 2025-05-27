import os

def test_backend_directory_exists():
    assert os.path.exists("backend")

def test_main_py_exists():
    assert os.path.exists("backend/main.py")

# A simple test to ensure pytest is working
def test_example():
    assert 1 + 1 == 2

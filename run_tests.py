"""
Runner script to execute all IMUCA test suites.
"""

import sys
import pytest

if __name__ == "__main__":
    # Disable any problematic plugins like anyio on Python 3.14 Windows
    exit_code = pytest.main(["-v", "-p", "no:anyio", "tests"])
    sys.exit(exit_code)

"""
End-to-end integration test that can be run with pytest.
This wraps the integration test to work with the test framework.
"""

import pytest
import sys
from pathlib import Path

# Add current directory to path so we can import test_integration
sys.path.insert(0, str(Path(__file__).parent))

from test_integration import IntegrationTest


@pytest.mark.integration
def test_complete_integration():
    """Test the complete watcher flow from HTTP to files."""
    test = IntegrationTest()
    test.run()


if __name__ == "__main__":
    # Allow running directly without pytest
    test_complete_integration()

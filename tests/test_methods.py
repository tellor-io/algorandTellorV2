from utils.helpers import call_sandbox_command
from utils.helpers import add_standalone_account

def setup_module(module):
    """Ensure Algorand Sandbox is up prior to running tests from this module."""
    call_sandbox_command("up")

class TestTellorFlex:
    '''Testing the tellor flex reporting contract'''

    def setup_method(self):
        _, self.tipper = add_standalone_account()
        _, self.reporter = add_standalone_account()
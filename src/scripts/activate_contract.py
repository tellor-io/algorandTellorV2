from typing import List
from src.scripts.multisig.multisig import send_multisig_tx

def activate_contract(app_id:int, app_ids:List[int]):
    
    send_multisig_tx(app_id=app_id, fn_name="activate_contract", app_args=None, foreign_apps=app_ids)
from typing import List
from src.scripts.multisig.multisig import send_multisig_tx

def activate_contract(medianizer_id:int, feed_ids:List[int]):
    
    send_multisig_tx(app_id=medianizer_id, fn_name="activate_contract", app_args=None, foreign_apps=feed_ids)
from scripts.multisig.multisig import send_multisig_tx


def change_medianizer(old_medianizer_app_id: int, new_medianizer_app_id: int):
    
    send_multisig_tx(app_id=old_medianizer_app_id, fn_name="change_medianizer", app_args=[new_medianizer_app_id])
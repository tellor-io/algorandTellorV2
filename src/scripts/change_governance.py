from scripts.multisig.multisig import send_multisig_tx


def change_governance(app_id: int, new_gov_address: str):

    send_multisig_tx(app_id=app_id, fn_name="change_governance", app_args=[new_gov_address])

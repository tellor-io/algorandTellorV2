from scripts.multisig.multisig import send_multisig_tx


def slash_reporter(feed_id: int):
    """
    Use the governance contract to approve or deny a value
    calls slash_reporter() on the contract, only callable by governance address
    """

    send_multisig_tx(app_id=feed_id, fn_name="slash_reporter", app_args=None, foreign_apps=None)

import sys
from src.utils.senders import send_multisig_tx
from src.utils.configs import get_configs


def change_governance(app_id: int, new_gov_address: str):

    send_multisig_tx(app_id=app_id, fn_name="change_governance", app_args=[new_gov_address], foreign_apps=None)


if __name__ == "__main__":

    #read config
    config = get_configs(sys.argv[1:])
    #parse app_ids of query_id from config
    app_ids = ([config.feeds[config.query_id].app_ids.medianizer[config.network]]
                    + list(config.feeds[config.query_id].app_ids.feeds[config.network])
    ) 

    print(f"changing governance address to {config.address}")


    print("now changing governance on query_id: ", config.query_id)

    for i in app_ids:
        change_governance(i, config.address)
        print(f"changed governance on app_id {i} to {config.address}")
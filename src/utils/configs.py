import argparse
from typing import List

import yaml
from box import Box


def get_configs(args: List[str]) -> Box:
    """get all signer configurations from passed flags or yaml file"""

    # read in configurations from yaml file
    with open("config.yml") as ymlfile:
        config = yaml.safe_load(ymlfile)

    # parse command line flags & arguments
    parser = argparse.ArgumentParser(description="Submit values to Tellor on Algorand")
    parser.add_argument(
        "-n",
        "--network",
        nargs=1,
        required=False,
        type=str,
        help="An EVM compatible network.",
    )
    parser.add_argument(
        "-qid",
        "--query-id",
        nargs=1,
        required=False,
        type=str,
        help="the query_id to submit values to",
    )

    parser.add_argument(
        "-qd", "--query-data", nargs=1, required=False, type=str, help="a description of the query_id (max 128 bytes)"
    )

    parser.add_argument(
        "-a", "--address", nargs=1, required=False, type=str, help="an account or multisig address on algorand"
    )

    parser.add_argument(
        "-tf",
        "--timestamp-freshness",
        nargs=1,
        required=False,
        type=int,
        help="time interval between data reports in seconds",
    )

    parser.add_argument(
        "-med",
        "--medianizer",
        nargs=1,
        required=False,
        type=int,
        help="app_id of the medianizer contract",
    )

    parser.add_argument(
        "-amt",
        "--amount",
        nargs=1,
        required=False,
        type=int,
        help="tip amount",
    )

    parser.add_argument(
        "-fid",
        "--feed-index",
        nargs=1,
        required=False,
        type=int,
        help="the index of the feed app id",
    )

    # get dict of parsed args
    if args is not None:
        cli_cfg = vars(parser.parse_args(args))

        # overwrite any configs from yaml file also given by user via cli
        for flag, arg in cli_cfg.items():
            if arg is not None:
                config[flag] = arg[0]

    # enable dot notation for accessing configs
    config = Box(config)

    return config

![CI](https://github.com/tellor-io/algorandTellor/actions/workflows/py39.yml/badge.svg)
[![codecov](https://codecov.io/gh/tellor-io/algorandTellor/branch/main/graph/badge.svg?token=XE8G0FARZL)](https://codecov.io/gh/tellor-io/algorandTellor)

# Overview
This repo contains the contracts, tests, and deployment scripts for Tellor contracts on Algorand. The high-level goal of Tellor on Alogrand is to reimplement Tellor on Algorand's smart contract system, the Algorand Virtual Machine (AVM), and enable the Algorand community to interact with Tellor in their native environment. Its closest Solidity equivalent is [TellorFlex](https://github.com/tellor-io/tellorFlex), which is the Tellor contract for non-mainnet-Ethereum EVM chains.

For more in-depth information about Tellor checkout our [documentation](https://docs.tellor.io/tellor/), [whitepaper](https://docs.tellor.io/tellor/whitepaper/introduction) and [website](https://tellor.io/).

# Key Features

## One data requester, one data reporter, one data feed
The Tellor PyTeal contract in this repo is a contract factory for a DeFi platform (for example, a betting contract, prediction market, stable coin, etc) to deploy an oracle for one particular data feed. This data feed can be a price feed, but it can also be a prediction (for example, the weather or an election outcome). In order to be clear about the data they expect, the data requester can deploy the contract with a `query_descriptor` string. This description can be a maximum of 128-characters, but is very useful for ensuring reporters understand the type of data they are to submit.

Each contract supports one stake from one data reporter, but opportunities for competition between reporters will be implemented in the near future.

## Ready-to-go price feeds
This repo comes equipped with ready-to-go price feeds. This means reporting values from these feeds via the CLI requires no configuration beyond providing accounts. These are the most commonly used data feeds in DeFi (BTCUSD, ETHUSD, etc.). These feeds are listed under `feeds` in the `config.yml` file.

## Open-source contract interaction
Just like on Ethereum, all Tellor contracts on Alogrand are open-source, freely available, and very forkable. Open-source deployment, testing, and contract interaction scripts in Python are supplied in the repo. These scripts can be called via the command line (very useful for github actions!), or via further python scripting. For CLI examples, see below.


# Setting up, interacting with, and testing the contract
**An example walkthrough using the BTCUSD query id**

Set up python environment
```
python3 -m venv venv
source activate venv
```


Install Dependencies
```
pip install -r requirements.txt
```

Test locally
```
python -m pytest
```

Deploy Bitcoin price feed contract
```
python -m src.scripts.deploy -qid BTCUSD -qd "bitcoin feed" -n devnet
```

Stake account (become data reporter)
```
python -m src.scripts.stake -n devnet
```

Report (submit value) BTCUSD price to contract
```
python -m src.scripts.report -qid BTCUSD -n devnet
```




## Maintainers <a name="maintainers"> </a>
This repository is maintained by the [Tellor team](https://github.com/orgs/tellor-io/people)


## How to Contribute<a name="how2contribute"> </a>
Join our Discord:
[<img src="https://raw.githubusercontent.com/tellor-io/tellorX/main/public/discord.png" width="24" height="24">](https://discord.gg/E5y6SZ8UV8)

Check out our issues log here on Github or feel free to reach out anytime [info@tellor.io](mailto:info@tellor.io)

## Copyright

Tellor Inc. 2022

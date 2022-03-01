![CI](https://github.com/tellor-io/algorandTellor/actions/workflows/py39.yml/badge.svg)
[![codecov](https://codecov.io/gh/tellor-io/algorandTellor/branch/main/graph/badge.svg?token=XE8G0FARZL)](https://codecov.io/gh/tellor-io/algorandTellor)

# Overview
This repo contains the contracts, tests, and deployment scripts for Tellor contracts on Algorand. The high-level goal of Tellor on Alogrand is to rebuild TellorFlex on Algorand's smart contract system, the Algorand Virtual Machine (AVM), and enable the Algorand community to interact with Tellor in their native environment. Its closest Solidity equivalent is [TellorFlex](https://github.com/tellor-io/tellorFlex), which is the Tellor contract for non-mainnet-Ethereum EVM chains.

For more in-depth information about Tellor checkout our [documentation](https://docs.tellor.io/tellor/), [whitepaper](https://docs.tellor.io/tellor/whitepaper/introduction) and [website](https://tellor.io/).

# Ready-to-go price feeds
This repo comes equipped with ready-to-go price feeds. This means reporting values from these feeds via the CLI requires no configuration beyond providing accounts. These are the most commonly used data feeds in DeFi (BTCUSD, ETHUSD, etc.). These feeds are listed under `feeds` in the `config.yml` file.


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
Join our Discord or Telegram:
[<img src="./public/telegram.png" width="24" height="24">](https://t.me/tellor)
[<img src="./public/discord.png" width="24" height="24">](https://discord.gg/g99vE5Hb)

Check out our issues log here on Github or feel free to reach out anytime [info@tellor.io](mailto:info@tellor.io)

## Copyright

Tellor Inc. 2022

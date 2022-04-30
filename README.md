![CI](https://github.com/tellor-io/algorandTellor/actions/workflows/py39.yml/badge.svg)
[![codecov](https://codecov.io/gh/tellor-io/algorandTellorv2/branch/main/graph/badge.svg?token=4LQW27GID5)](https://codecov.io/gh/tellor-io/algorandTellorv2)
# Overview
For upwards of 2 years, Tellor has been live on Ethereum mainnet. In an effort to facilitate a multi-chain ecosystem, the Tellor oracle has been re-implemented for the Algorand Virtual Machine (AVM). On Algorand, Tellor continues to be secure, decentralized, and easy to integrate. 

The primary contracts of the Tellor oracle on Algorand are the feed contracts, the medianzier contracts, and the governance contract. At a high level, each price feed, or “queryId”, uses a “medianizer contract” to calculate the median between 5 independent data submissions on 5 independent “feed contracts”. Tellor on Algorand implements a vigilant governance contract that prevents bad actors from interfering with the security of price feeds.

In order for a protocol to request data, or “tip” a price feed (e.g. BTC/USD spot price), an Algorand account or contract can send a reward to the feed contract claimable only by a data reporter when they update the price feed. With a minimum frequency of the Algorand block time interval, accounts, contracts, and protocols can schedule tipping and data reporting at whatever frequency fits their needs, providing high flexibility for protocols and reporters alike.

When Algorand accounts tip the feed contract, “reporters” can claim the tip by submitting data from an accurate source that fulfills the request of data by the tipper. They must also provide a bond, or “stake” for permission to report data. When the reporter completes the data submission, the value and timestamp are saved on-chain to the feed contract, and the median value on the medianizer contract updates. Then, the feed contract transfers the “tip”, or the reward for the data submission, to the reporter, with the exception of a 2% fee to the governance contract.

To incentivize healthy and accurate data feeds, Tellor on Algorand implements the added security of Algorand through the use of the ALGO token as the native token of the oracle. This means that staking, tipping, and reporter rewards transact using ALGO transfers. Further, Tellor on Algorand implements the medianizer contract in order to prevent one bad-actor reporter from skewing a data feed. Tellor’s governance can also suspend bad-actor reporters and confiscate their stake. Finally, the feed contract prevents reporters from immediately withdrawing their stake, which holds bad-actor reporters accountable to unhealthy data reports.

Governance in the Tellor Algorand oracle serves to deploy, maintain, and monitor the health of all Tellor data feeds. First, governance is responsible for the deployment and setup of feed contracts and a medianizer contract for a new data feed. Second, governance is responsible for monitoring the health of the feeds. Third, if governance detects a bad actor, the governance is responsible for disputing the feed.

In short, Tellor on Algorand is a secure, decentralized, and easy-to-use re-implementation of Tellor on Ethereum for the Algorand network. Tellor on Algorand serves to broaden the Tellor network and extend the Algorand ecosystem.


For more in-depth information about Tellor checkout our [documentation](https://docs.tellor.io/tellor/), [whitepaper](https://docs.tellor.io/tellor/whitepaper/introduction) and [website](https://tellor.io/).

# This repo comes with...

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

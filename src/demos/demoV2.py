from time import time

from algosdk import encoding
from algosdk.error import AlgodHTTPError
from algosdk.logic import get_application_address

from src.scripts.scripts import Scripts
from src.utils.accounts import Accounts
from src.utils.helpers import _algod_client
from src.utils.testing.resources import fundAccount
from src.utils.util import getAppGlobalState

print("TELLOR APPLICATION WALKTHROUGH")

print("deployment...")

client = _algod_client()
accounts = Accounts(client)
scripts = Scripts(client, accounts.tipper, accounts.reporter, accounts.governance, contract_count=5)

fundAccount(client, accounts.governance.address())
fundAccount(client, accounts.tipper.getAddress())
fundAccount(client, accounts.reporter.getAddress())
for i in accounts.reporters:
    fundAccount(client, i.getAddress())
fundAccount(client, accounts.bad_actor.getAddress())
# constructor variables
query_id = "btc/usd"
query_data = "this is my description of query_id `btc/usd"
timestamp_freshness = 3600
multisigaccounts_sk = accounts.multisig_signers_sk

# deploy contract
feed_ids = scripts.deploy_tellor_flex(
    query_id=query_id,
    query_data=query_data,
    timestamp_freshness=timestamp_freshness,
    multisigaccounts_sk=multisigaccounts_sk,
)
medianizer_id = scripts.deploy_medianizer(
    timestamp_freshness=timestamp_freshness, query_id=query_id, multisigaccounts_sk=multisigaccounts_sk
)
activate_medianizer = scripts.activate_contract(multisigaccounts_sk=multisigaccounts_sk)
connect_feeds_medianizer = scripts.set_medianizer(multisigaccounts_sk=multisigaccounts_sk)

print("5 feed contracts deployed! application id: ", feed_ids)
print("medianizer contract deployed! application id: ", medianizer_id)
print("medianizer contract active! transaction id: ", activate_medianizer)
print("feeds connected to medianizer! transaction ids: ", connect_feeds_medianizer)

for i in feed_ids:
    scripts.feed_app_id = i
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    scripts.tip(100000)
# print contract attributes
state = getAppGlobalState(client, appID=feed_ids[0])
query_id = state[b"query_id"]
query_data = state[b"query_data"]
stake_amount = state[b"stake_amount"]
governance = state[b"governance_address"]
tip_amount = state[b"tip_amount"]
medianizer = state[b"medianizer"]
timestamp_freshness = state[b"timestamp_freshness"]

print("---------------")

print("---feed contract variables set on app creation---")
print("query id (unique indicator of data requested): ", query_id)
print("query data (in depth descriptor of the query id)", query_data)
print("stake amount in ALGO to become the data reporter: ", stake_amount)
print("tip amount in ALGO to incentivize the data reporter: ", tip_amount)
print("medianizer feed is connected to: ", medianizer)
print("timestamp age interval: ", timestamp_freshness)
print("governance address: ", encoding.encode_address(governance))
print("reporter address set later!")

print("---------------")

state = getAppGlobalState(client, appID=medianizer_id)
query_id = state[b"query_id"]
governance = state[b"governance"]
timestamp_freshness = state[b"timestamp_freshness"]

print("---medianizer contract variables set on app creation---")
print("query id (unique indicator of data requested): ", query_id)
print("timestamp age interval: ", timestamp_freshness)
print("governance address: ", encoding.encode_address(governance))

print("---------------")
# reporter submits good value
good_value = 40000
for i in range(3):
    scripts.reporter = accounts.reporters[i]
    scripts.feed_app_id = feed_ids[i]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    print(f"Reporter {i+1} staking...")

    # reporter stakes
    scripts.stake()
    print(f"Reporter {i+1} now staked on feed {feed_id}!")
    scripts
    state = getAppGlobalState(client, appID=feed_ids[i])
    reporter = state[b"reporter_address"]
    staking_status = state[b"staking_status"]
    print("data reporter address: ", encoding.encode_address(reporter))
    print("staking status (1 if staked, 0 if not staked): ", staking_status)
    timestamp = int(time() - 500)
    scripts.report(query_id=query_id, value=good_value, timestamp=timestamp)
    print(f"I'm reporting, {query_id}, at, {good_value}, on timestamp: {timestamp}")
    state = getAppGlobalState(client=client, appID=medianizer_id)
    median = state[b"median"]
    median_timestamp = state[b"median_timestamp"]

    print(f"Median value: {median}, timestamp: {median_timestamp} after {i+1} report(s)")

    print("---------------")
    good_value += 500

print(f"reporter trying to withdraw stake...")
try:
    scripts.withdraw()
except AlgodHTTPError:
    print(f"Error: need to request a withdraw and wait 7 days to withdraw ...")
print("---------------")

print(f"reporter requesting to withdraw")
scripts.request_withdraw()
state = getAppGlobalState(client, appID=feed_ids[i])
reporter = state[b"reporter_address"]
staking_status = state[b"staking_status"]
print(f"reporter has requested withdrawal, staking status is now {staking_status}")
print("---------------")

print(f"reporter trying to withdraw immediately after request ...")
try:
    scripts.withdraw()
except AlgodHTTPError:
    print("Error: can't withdraw must wait 7 days to get stake back!")

# reporter submits bad value
bad_value = 40
scripts.reporter = accounts.reporters[1]
scripts.feed_app_id = feed_ids[1]
scripts.report(query_id=query_id, value=bad_value, timestamp=int(time() - 500))
print("I'm a bad actor and I'm reporting ", query_id, " at", bad_value)
print("---------------")

# governance takes away submission privileges from reporter
scripts.slash_reporter(multisigaccounts_sk=multisigaccounts_sk)
state = getAppGlobalState(client, appID=feed_ids[1])
reporter = state[b"reporter_address"]
staking_status = state[b"staking_status"]

print(f"reporter has been slashed, staking status is {staking_status}")
print("(1 if staked, 0 if not staked, 2 if requesting withdrawal)")
print("---------------")

# trying to report after being slashed
print("reporter trying to report after being slashed")
try:
    scripts.report(query_id=query_id, value=good_value, timestamp=int(time() - 500))
except AlgodHTTPError:
    print("Error: can't report you've been slashed and no longer staked!")

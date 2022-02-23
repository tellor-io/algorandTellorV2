from src.scripts.scripts import Scripts
from src.utils.accounts import Accounts
from src.utils.helpers import _algod_client
from src.utils.testing.resources import getTemporaryAccount
from src.utils.util import getAppGlobalState

client = _algod_client()
accounts = Accounts(client)
scripts = Scripts(client, accounts.tipper, accounts.reporter, accounts.governance)

print("TELLOR APPLICATION WALKTHROUGH")

print("deployment...")
# deploy contract
app_id = scripts.deploy_tellor_flex(query_id="btc/usd", query_data="this is my description of query_id `btc/usd")

print("contract deployed! application id: ", app_id)

# print contract attributes
state = getAppGlobalState(client, appID=app_id)
tipper = state[b"tipper"]
query_id = state[b"query_id"]
query_data = state[b"query_data"]
stake_amount = state[b"stake_amount"]
governance = state[b"governance_address"]
num_reports = state[b"num_reports"]

print("---contract variables set on app creation---")
print("tipper address (the data requester): ", tipper)
print("query id (unique indicator of data requested): ", query_id)
print("query data (in depth descriptor of the query id)", query_data)
print("stake amount in ALGO to become the data reporter: ", stake_amount)
print("number of values reported: ", num_reports)
print("governance address: ", governance)
print("reporter address set later!")

print("---------------")

print("staking...")
# reporter stakes
scripts.stake()
print("now staked!")

state = getAppGlobalState(client, appID=app_id)
reporter = state[b"reporter_address"]
staking_status = state[b"staking_status"]
print("data reporter address: ", reporter)
print("staking status (1 if staked, 0 if not staked): ", staking_status)

# reporter submits good value
query_id = b"btc/usd"
value = b"$40,000"

scripts.report(query_id=query_id, value=value)
print("I'm reporting ", query_id, " at ", value)

# reporter submits bad value
bad_value = b"$42"
scripts.report(query_id=query_id, value=bad_value)
print("I'm a bad actor and I'm reporting ", query_id, " at", bad_value)

# governance takes away submission privileges from reporter
print("governance takes away my stake and right to report")
scripts.vote(0)

# # another reporter reopens feed
# scripts.reporter = getTemporaryAccount(client)
# scripts.stake()

# state = getAppGlobalState(client, appID=app_id)
# print("new reporter address: ", state[b"reporter_address"])


# scripts.report(query_id=query_id, value=value)

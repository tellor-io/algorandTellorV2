"""Tests for datafeeds and their sources"""

from assets.asset import Asset

from utils.configs import get_configs

def test_algo_usd_feed():

    # read config
    config = get_configs(None)

    #read sources
    sources=config.apis["ALGOUSD"]
    
    # create data feed
    asset = Asset(query_id="ALGOUSD", sources=sources)

    asset.update_price()
    value = asset.price

    assert isinstance(value, int)
    assert value > 0
    assert value < 1e7

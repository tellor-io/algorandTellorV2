"""DataSource class"""
from typing import Dict

import requests


class DataSource:
    def __init__(self, query_id, request_url, request_parsers, subgraph=False):
        self.query_id = query_id
        self.request_url = request_url
        self.request_parsers = request_parsers
        self.subgraph = subgraph

    def get_price(api_info: Dict) -> float:
        """
        Fetches price data from centralized public web API endpoints
        Returns: (str) ticker price from public exchange web APIs
        Input: (list of str) public api endpoint with any necessary json parsing keywords
        """

        # Request JSON from public api endpoint
        rsp = requests.get(api_info["url"]).json()

        # Parse through json with pre-written keywords
        for keyword in api_info["keywords"]:
            rsp = rsp[keyword]

        # return price (last remaining element of the json)
        price = float(rsp)
        return price

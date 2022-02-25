"""
Asset class
"""
import time
from typing import Dict

import requests


class Asset:
    def __init__(self, query_id, sources: Dict):
        """
        Inputs:
            asset (str): name of asset as represe
        """
        self.query_id = (query_id,)
        self.price = (0,)
        self.string_price = ("0",)
        self.timestamp = (0,)
        self.last_pushed_price = (0,)
        self.time_last_pushed = 0
        self.precision = 1e6
        self.sources = sources

    def add_api_endpoint(self, api):
        self.api_list.append(api)

    def update_price(self):
        self.timestamp = int(time.time())
        self.price = int(self.medianize())

    def medianize(self):
        """
        Medianizes price of an asset from a selection of centralized exchange APIs
        """
        final_results = []

        if not self.sources:
            raise ValueError("Cannot medianize prices with data sources. No APIs added for asset.")

        for source in self.sources.keys():
            price = self.fetch_price_from_sources(self.sources[source])
            final_results.append(price)

        # sort final results
        final_results.sort()
        return final_results[len(final_results) // 2]

    def fetch_price_from_sources(self, source: Dict) -> int:
        """
        Fetches price data from centralized public web API endpoints
        Returns: (str) ticker price from public exchange web APIs (decimals rounded down)
        Input: (list of str) public api endpoint with any necessary json parsing keywords
        """

        # Request JSON from public api endpoint
        rsp = requests.get(source["url"]).json()

        # Parse through json with pre-written keywords
        for keyword in source["keywords"]:
            rsp = rsp[keyword]

        # return price (last remaining element of the json)
        return int(float(rsp))

    def __str__(self):
        return f"""Asset: {self.name} query_id: {self.query_id} price: {self.price} timestamp: {self.timestamp}"""

    def __repr__(self):
        return f"""Asset: {self.name} query_id: {self.query_id} price: {self.price} timestamp: {self.timestamp}"""

    def __eq__(self, other):
        if self.name == other.name and self.query_id == other.query_id:
            return True
        return False

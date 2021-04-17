#!/usr/bin/env python

import os
import waitress
from flask import Flask, jsonify
import beeline
from beeline.middleware.flask import HoneyMiddleware
from beeline.patch.requests import *


import requests

# I don't exactly know what these slot numbers mean, but I know this exact
# result means that there are no slots available.
KNOWN_NO_SLOTS = {'1': False, '2': False}

app = Flask(__name__)
HoneyMiddleware(app)


@app.route('/availability/<zip_code>')
def availability(zip_code):
    store_response = requests.get(
        'https://www.riteaid.com/services/ext/v2/stores/getStores',
        params={
            'address': zip_code,
            'attrFilter': 'PREF-112',
            'fetchMechanismVersion': '2',
            'radius': '50',
        },
    ).json()['Data']['stores']
    stores = []

    for store_data in store_response:
        store_id = store_data['storeNumber']

        slots = requests.get(
            'https://www.riteaid.com/services/ext/v2/vaccine/checkSlots',
            params={
                'storeNumber': store_id,
            },
        ).json()['Data']['slots']

        possible_availability = slots != KNOWN_NO_SLOTS

        stores.append({
            'id': store_id,
            'address': store_data['address'],
            'possible_availability': possible_availability,
            'zip': store_data['zipcode'],
            'phone': store_data['fullPhone'],
        })

    return jsonify(stores)


@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    return response


if __name__ == "__main__":
    key = os.environ.get('HONEYCOMB_API_KEY')
    if key:
        beeline.init(
            writekey=key,
            dataset='riteaid-covid',
            service_name='riteaid-covid-http',
        )

    waitress.serve(app, listen='*:80')

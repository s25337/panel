
from flask import Blueprint, jsonify, request
import json
import os

BASE_URL = "http://31.11.238.45:8081/terrarium"
ENDPOINT_ADD_MODULE = f"{BASE_URL}/module"
ENDPOINT_SEND_DATA = f"{BASE_URL}/dataTerrarium"
ENDPOINT_UPDATE_SETTING = f"{BASE_URL}/updateSetting"

TIMEOUT = 5
SYNC_INTERVAL = 300  # 5 minutes in seconds
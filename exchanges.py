import urllib
import httplib
import json
import random
import time
import datetime
import hmac
import hashlib
import decimal
import sqlite3
import os.path
import socket
import colorconsole.terminal
import math

import settings

# JSON APIs
# (host, uri, symbol_translation)
MARKET_ALLCOIN_API = ("www.allcoin.com", "/api1/pairs", {"HIC": "HIRO"})
MARKET_ATOMIC_TRADE_API = ("www.atomic-trade.com", "/SimpleAPI?a=marketsv2", {})
MARKET_MINTPAL_API = ("api.mintpal.com", "/v1/market/summary/", {})
MARKET_POLONIEX_API = ("poloniex.com", "/public?command=returnTicker", {})
MARKET_BITTREX_API = ("bittrex.com", "/api/v1/public/getmarketsummaries", {})
MARKET_CCEX_API = ("c-cex.com", "/t/prices.json", {})
MARKET_CRYPTOALTEX_API = ("www.cryptoaltex.com", "/api/public.php", {})

price_index = {}

def std_error(msg):
    print(msg)

error = std_error

def get_exchange_data(exc):
    try:
        conn = httplib.HTTPSConnection(exc[0])
        conn.request("GET", exc[1])
        resp = conn.getresponse()
        obj = json.load(resp)
        conn.close()
        return obj
    except socket.gaierror:
        error("Cannot resolve %s" % exc[0])
    except socket.error:
        error("Generic socket error")
        
def get_exchange_data_strip_comma(exc):
    try:
        conn = httplib.HTTPSConnection(exc[0])
        conn.request("GET", exc[1])
        resp = conn.getresponse()
        data = resp.read()
        spl = data.split(",")
        data = "".join([",".join(spl[:-1]), spl[-1]])
        obj = json.loads(data)
        conn.close()
        return obj
    except socket.gaierror:
        error("Cannot resolve %s" % exc[0])
        
def update_exchanges():
    
    def process_allcoin(js):
        ret = {}
        if js:
            for sym in settings.WALLETS:
                try:
                    ret[sym] = decimal.Decimal(js["data"]["%s_btc" % sym.lower()]["trade_price"])
                except KeyError:
                    pass
        return ret
        
    def process_mintpal(js):
        ret = {}
        for o in js:
            if o["exchange"] == "BTC":
                sym = o["code"]
                ret[sym] = decimal.Decimal(o["last_price"])
        return ret

    def process_poloniex(js):
        ret = {}
        if js:
            if js["BTC_LTC"]:
                ltc_p = decimal.Decimal(js["BTC_LTC"]["last"])
            else:
                ltc_p = None
                
            for x in js:
                par = x.split("_")
                sym = par[1]
                p = decimal.Decimal(js[x]["last"])
                if (par[0] == "LTC") and (ltc_p):
                    p = p * ltc_p
                if not(par[1] in ret):
                    ret[sym] = p
            return ret
        
    def process_bittrex(js):
        ret = {}
        for x in js["result"]:
            par = x["MarketName"].split("-")
            if par[0] == "BTC":
                sym = par[1]
                try:
                    p = decimal.Decimal(x["Last"])
                    ret[sym] = p
                except KeyError:
                    error("Processing %s, KeyError" % par[1])
                except TypeError:
                    error("Processing %s, TypeError" % par[1])
        return ret
        
    def procesar_ccex(js):
        ret = {}
        for x in js:
            par = x.split("-")
            if par[1] == 'btc':
                ret[par[0].upper()] = decimal.Decimal(js[x]['lastprice'])
        return ret
        
    def parse_ret(rt, trans):
        global price_index
        if rt:
            for x in rt:
                nx = x
                if trans and (x in trans):
                    nx = trans[x]
                try:
                    price_index[nx].append(rt[x])
                except KeyError:
                    price_index[nx] = [rt[x]]
               
    def procesar_cryptoaltex(js):
        ret = {}
        for x in js:
            ret[x] = decimal.Decimal(js[x]['last_trade'])
        return ret

    """js = get_exchange_data_strip_comma(MARKET_ATOMIC_TRADE_API) # Still solving some issues here
    print(js)"""
        
    parse_ret(process_allcoin(get_exchange_data(MARKET_ALLCOIN_API)), MARKET_ALLCOIN_API[2])
    parse_ret(process_mintpal(get_exchange_data(MARKET_MINTPAL_API)), MARKET_MINTPAL_API[2])
    parse_ret(process_poloniex(get_exchange_data(MARKET_POLONIEX_API)), MARKET_POLONIEX_API[2])
    parse_ret(process_bittrex(get_exchange_data(MARKET_BITTREX_API)), MARKET_BITTREX_API[2])
    parse_ret(procesar_ccex(get_exchange_data(MARKET_CCEX_API)), MARKET_CCEX_API[2])
    parse_ret(procesar_cryptoaltex(get_exchange_data(MARKET_CRYPTOALTEX_API)), MARKET_CRYPTOALTEX_API[2])

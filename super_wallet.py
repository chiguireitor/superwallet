import urllib
import httplib
import bitcoinrpc
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

import sys
import settings
import exchanges

# Para los colores de la consola https://code.google.com/p/colorconsole/wiki/PageName?tm=6

conexiones_btc = {}
params_btc = {"current_wallet": "N/A"}

screen = colorconsole.terminal.get_terminal()
screen.set_title("Super Wallet")

btc_value = 0

execute = True

def asegurar_conexion(sym):
    wallet_uso = settings.WALLETS[sym]
    if not(sym in conexiones_btc):
        try:
            conexiones_btc[sym] = bitcoinrpc.connect_to_remote(wallet_uso["user"], wallet_uso["pass"], host=wallet_uso["host"], port=wallet_uso["port"])
            screen.set_color(10, 0)
            print(" * Connected to Wallet: %s" % sym)
        except socket.error, err:
            screen.set_color(12, 0)
            print(" * Cannot connect to Wallet: %s" % sym)
            
    return wallet_uso

def error(msg):
    screen.set_color(12, 0)
    print(msg)
    
def salir(params):
    """exit
    Close the application
    """
    global execute
    print("Bye!")
    execute = False
  
def connect(params):
    """connect [wallet | *]
    Connect to a given wallet or to all the wallets.
    
    When passed * as parameter, connects to all the wallets configured.
    """
    if len(params) == 1:
        if params[0] == "*":
            for x in settings.WALLETS:
                asegurar_conexion(x)
        else:
            try:
                #conexiones_btc[params[0]] = asegurar_conexion(params[0])
                asegurar_conexion(params[0])
                print(conexiones_btc[params[0]])
                params_btc["current_wallet"] = params[0]
            except KeyError:
                error("Wallet doesn't exists: %s" % params[0])
    else:
        error("Usage: connect [* | SYMBOL]")
        
def use(params):
    """use wallet
    Mark a wallet as current wallet to be used in subsequent operations.
    """
    if len(params) == 1:
        #global current_wallet
        
        if params[0] in conexiones_btc:
            params_btc["current_wallet"] = params[0]
        else:
            error("Wallet doesn't exists: %s" % params[0])
    else:
        error("Usage: use SYMBOL")
        
def balance(params):
    """balance [account [minconf]]
    Get balance of the wallet or a specific account.
    
    You can optionally specify the minimum number of confirmations to consider.
    """
    try:
        if len(params) == 0:
            bal = conexiones_btc[params_btc["current_wallet"]].getbalance()
            params_btc["bal_%s" % params_btc["current_wallet"]] = bal
        elif len(params) == 1:
            bal = conexiones_btc[params_btc["current_wallet"]].getbalance(params[0])
        elif len(params) == 2:
            bal = conexiones_btc[params_btc["current_wallet"]].getbalance(params[0], int(params[1]))
        print(bal)
    except KeyError:
        error("Invalid Wallet: %s" % params_btc["current_wallet"])
        
def accounts(params):
    """accounts - list accounts
    Print a list of the accounts of the current wallet.
    """
    try:
        unconf = conexiones_btc[params_btc["current_wallet"]].listaccounts(minconf=0, as_dict=True)
        conf = conexiones_btc[params_btc["current_wallet"]].listaccounts(minconf=6, as_dict=True)
        
        for x in conf:
            print(" - %s: %f (%f unconfirmed)" % (x, float(conf[x]), float(unconf[x]) - float(conf[x])))
    except KeyError:
        error("Invalid Wallet: %s" % params_btc["current_wallet"])
        
def sendfrom(params):
    """sendfrom [account] address amount
    Send a given amount from an account of the current wallet.
    """
    if len(params) == 3:
        conexiones_btc[params_btc["current_wallet"]].sendfrom(params[0], params[1], float(params[2]))
    elif len(params) == 2:
        conexiones_btc[params_btc["current_wallet"]].sendfrom("", params[0], float(params[1]))
    else:
        error("Usage: sendfrom ACCOUNT ADDRESS AMOUNT")
        
def move(params):
    """move [accountfrom] accountto amount
    Move a given amount from an account to another of the current wallet.
    """
    if len(params) == 3:
        conexiones_btc[params_btc["current_wallet"]].move(params[0], params[1], float(params[2]))
    elif len(params) == 2:
        conexiones_btc[params_btc["current_wallet"]].move("", params[0], float(params[1]))
    else:
        error("Usage: sendfrom ACCOUNT ADDRESS AMOUNT")
        
def update(params):
    """update [*]
    Update the current account or all accounts.
    
    When given no parameters, updates the current wallet.
    
    When passed * as the parameter, updates all the wallets.
    """
    if len(params) == 0:
        try:
            bal = conexiones_btc[params_btc["current_wallet"]].getbalance()
            params_btc["bal_%s" % params_btc["current_wallet"]] = bal
        except KeyError:
            error("Invalid Wallet: %s" % params_btc["current_wallet"])
        except httplib.CannotSendRequest:
            error("Cannot connect to wallet: %s" % params_btc["current_wallet"])
    elif (len(params) == 1) and (params[0] == "*"):
        for x in conexiones_btc:
            try:
                bal = conexiones_btc[x].getbalance()
                params_btc["bal_%s" % x] = bal
                screen.set_color(10, 0)
                print("Updated %s" % x)
            except socket.error:
                params_btc["bal_%s" % x] = "N/A"
                error("Couldn't update %s" % x)
            except httplib.CannotSendRequest:
                error("Cannot connect to wallet: %s" % x)
    
def help(params):
    """help [command]
    Get help about commands.
    
    When invoked without params, it prints a list of commands with a short description.
    
    When invoked with a parameter it gives help about that command.
    """
    if len(params) == 0:
        for x in comandos:
            if comandos[x].__doc__:
                desc = comandos[x].__doc__.split("\n")[0]
            else:
                desc = ""
                
            print("%s - %s" % (x, desc))
        print("Type help command to get help on a command")
    else:
        try:
            print comandos[params[0]].__doc__
        except KeyError:
            error("Command %s not found" % params[0])
            
def update_btc_value():
    total = decimal.Decimal(0)
    for x in exchanges.price_index:
        n = decimal.Decimal(len(exchanges.price_index[x]))
        s = sum(exchanges.price_index[x])
        r = s/n
        try:
            p = decimal.Decimal(params_btc["bal_%s" % x]) * r
            total = total + p
            params_btc["btc_price_%s" % x] = p
        except KeyError:
            pass
        except TypeError:
            error("Failed updating: %s - TypeError" % x)
            error(params_btc["bal_%s" % x])
        except decimal.InvalidOperation:
            error("Nondecimal value for %s" % x)
        
    global btc_value
    btc_value = float(total)
            
def excs(params):
    """excs - Downloads exchanges tickers
    Read all the exchanges data, parsing their output to calculate wallets' values.
    """
    exchanges.update_exchanges()
    update_btc_value()
    
def cue(params):
    """cue - Connect, Update and Exchanges
    Connects, Updates and reads Exchanges from all the wallets.
    """
    connect(["*"])
    update(["*"])
    excs([])
    
def donate(params):
    """donate - Prints developer & donation information
    Thanks for your support :)
    """
    screen.set_color(15, 0)
    print("Thanks for your support, every bit counts!")
    def prn(sym, addr, idx):
        bgalt = [1, 4][idx % 2]
        screen.set_color(15, bgalt)
        sys.stdout.write("\t%s: " % sym)
        screen.set_color(14, bgalt)
        sys.stdout.write("\t%s\t\n" % addr)
        
    # Please don't remove these, if you make modifications, add your own :) / Be nice ;)
    print("Chiguireitor's (Original Dev):")
    prn("BTC", "1JRY7TNYdrexWx1E7tdSrgvtNgQwssskmw", 0)
    prn("LTC", "Lhz69G8YZHdyj2SL1wT97w5Fgjcv4CFKfq", 1)
    prn("DOGE", "DSF86fUZEAWksA8ArYsAocFRiQoCKPSpmt", 2)
    prn("SKC", "SYo6GiosDzfbX8XWhs1JKy2wb5AZjByAs5", 3)
    prn("GRS", "FhyWxmRb4FPF5nHLDZwqwr7PHcheXr7A77", 4)
    prn("ECC", "ERJUZieVjUpkrzNMMLyPK3kUDvrj8WkKDk", 5)
    prn("LIM", "8pdEibbZbAKmP8tn2XBKgWJoEm5bKx6R8S", 6)
    prn("KSC", "KeP8h5UU4msTTJi9PGmdLnVFEEwHxFcyHa", 7)
    prn("HVC", "H7KxZ1jnpFMN9naEaAjA9bRwqJQdaGFwRe", 8)
    prn("MAX", "mHhF49UNoWednzpBYUJhMDThGAkMmDHzX7", 9)
    prn("MEC", "MKmzgAHKvC36KTy4UNAfzSotSWbeKuLfJv", 10)
    prn("GLB", "12L8JG15C4jr3hxE9V28iJ1DZnGLszbbGp", 11)
  
comandos = {
    "exit": salir,
    "connect": connect,
    "use": use,
    "balance": balance,
    "sendfrom": sendfrom,
    "move": move,
    "accounts": accounts,
    "update": update,
    "help": help,
    "excs": excs,
    "cue": cue,
    "donate": donate
}

screen.clear()

def draw_menu(w, h):
    screen.set_color(14, 1)
    screen.print_at(0, 0, " "*w)
    screen.print_at(0, 0, "Super Wallet - Total Value: %0.8f BTC | Total Wallets: %i | Current wallet: %s" % (btc_value, len(conexiones_btc), params_btc["current_wallet"]))
    
    screen.set_color(14, 1)
    pidx = 1
    for x in conexiones_btc:
        try:
            bal = str(params_btc["bal_%s" % x])
        except KeyError:
            bal = "0.00000000"
            
        if ("btc_price_%s" % x) in params_btc:
            screen.set_color(14, 1)
        else:
            screen.set_color(7, 8)
            
        wll = "".join([" ", x, ": ", " " * (24 - len(bal) - len(x)), bal, " "])
        screen.print_at(w - 28, pidx, wll)
        pidx += 1
    
    screen.set_color(15, 0)

def clear_espacio_escritura(w, h):
    rct = " " * (w - 28)
    screen.set_color(15, 0)
    for x in range(0, 40):
        print(rct)
        
def clear_espacio_prompt(w):
    rct = " " * (w - 28)
    screen.set_color(15, 0)
    print(rct)
    
screen.set_color(15, 0)
screen.clear()
screen.gotoXY(0, 2)
print("type help to get info on what commands are available")
if "DEFINEYOURSYMBOLS" in settings.WALLETS:
    print("You haven't configured settings.py, open it in a text editor and configure your daemons")

exchanges.error = error
while (execute):
    w = screen.columns()
    h = screen.lines()

    draw_menu(w, h)
    screen.gotoXY(0, 1)
    clear_espacio_prompt(w)
    screen.gotoXY(0, 1)
    com = raw_input("cmd>").split(" ")
    clear_espacio_escritura(w, h)
    screen.gotoXY(0, 2)
    #screen.clear()
    #screen.gotoXY(0, 2)
    cmd = None
    try:
        cmd = comandos[com[0]]
    except KeyError:
        print("Command not found: %s" % com[0])
    except socket.error:
        print("Socket error")
        
    if cmd:
        cmd(com[1:])

screen.reset()
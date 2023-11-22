import threading
import time
import io
from binance import Client
import datetime
import matplotlib as plt
import pandas as pd
from typing import Final
from telegram import Update, ForceReply, Message
from telegram.ext import (Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters)
import requests

#CoinMarketCap API
CoinMktCap_API: Final = '[Your Own CoinMarketCap API Key]'

# Telegram Bot Token
Telegram_Token: Final = 'Telegram Token'
BotUserName: Final = 'Name of your Telegram Bot'
CRYPTO_INPUT = 1

# To store and hold the crypto wanted price
portfolio = {}
alert_inputs = {'Crypto_Symbol': [], '< / >': [], 'Currency':[], 'Price':[]}
alert_inputs = pd.DataFrame(alert_inputs)


def start(update: Update, context: CallbackContext) -> None:
    """Sends a message when the start is issued."""
    user = update.effective_user
    update.message.reply_html(
        rf"Hi {user.mention_html()}! 👋",
        reply_markup= ForceReply(selective = True),
    )
    update.message.reply_text('Welcome to @ECON3086_CryptoPriceAlertbot! 🤗')
    update.message.reply_text('Type /help for more information.')

def help_command(update: Update, context: CallbackContext) -> None:
    """Sends a message when the command /help is issued."""
    update.message.reply_text(
        """
/start -> Starts the ECON3086_CryptoPriceAlertBot!
/help -> Shows all available commands
/my_portfolio -> Shows your current portfolio holdings
/current_price -> Get current real time price of your desired crypto coin & currency.
/set_alert -> Get real time alert when the price of your desired crypto coin has reached your target price.
/remove_alert -> Remove any price alert of your choice.
/check_alert -> Shows current price alert in place.
/place_trade -> Buy or sell your desired crypto
/exit -> Ends chat with @ECON3086_CryptoPriceAlertbot
        """)

def portfolio_command(update: Update, context: CallbackContext) -> None:
    """Shows current portfolio."""
    update.message.reply_text("Current Portfolio Holdings: \n{}".format(check_portfolio()))
    # update.message.reply_text(check_portfolio())

def check_portfolio():
    to_return = ""
    for symbol, quantity in portfolio.items():
        to_return+=f"{symbol}: {quantity}\n"
    return to_return

def place_trade_command(update: Update, context: CallbackContext) -> None:
    text = "What would like to do (buy or sell), what crypto coin (crypto symbol) and what is the volume would you like to trade?\nExample: BUY BTC 50"
    update.message.reply_text(text)
    return CRYPTO_INPUT

def process_crypto_input_trade(update: Update, context: CallbackContext) -> None:
    message: Message = update.message
    input_text = message.text
    # Split the user's input into the crypto symbol, currency symbol, and desired volume
    list_info = input_text.split(' ')
    action: str = list_info[0].upper()
    crypto_symbol: str = list_info[1].upper()
    volume: float = float(list_info[-1])
    instant_trade(action, crypto_symbol, volume, update)
    return ConversationHandler.END


def instant_trade(action, symbol, quantity, update: Update):
    if action == 'BUY':
        buy(symbol, float(quantity), update)
    elif action == 'SELL':
        sell(symbol, float(quantity), update)
    else:
        update.message.reply_text("Invalid. Please choose 'buy' or 'sell'.")

def buy(symbol, quantity, update: Update):
    if symbol in portfolio:
        portfolio[symbol] += quantity
    else:
        portfolio[symbol] = quantity
    update.message.reply_text(f"You have bought {quantity} {symbol}.")

def sell(symbol, quantity, update: Update):
    if symbol in portfolio and portfolio[symbol] >= quantity:
        portfolio[symbol] -= quantity
        update.message.reply_text(f"You have sold {quantity} {symbol}.")
    else:
        update.message.reply_text(f"You do not have enough {symbol} to sell.")




def exit_command(update: Update, context: CallbackContext) -> None:
    """Sends a goodbye message when /exit is issued."""
    update.message.reply_text('Thank you. Bye bye!')
    exit()



def current_price_command(update: Update, context: CallbackContext) -> None:
    message: Message = update.message
    text = "⚠️ Please enter the crypto coin symbol, currency symbol: [crypto symbol] [currency symbol].\nExample: BTC USD"
    update.message.reply_text(text)

    # Use API to fetch
    context.user_data['state'] = CRYPTO_INPUT
    return CRYPTO_INPUT


def process_crypto_input_current(update: Update, context: CallbackContext) -> None:
    message: Message = update.message
    input_text = message.text
    # Split the user's input into the crypto symbol, currency symbol, and desired price
    list_info = input_text.split(' ')
    crypto_symbol: str = list_info[0].upper()
    currency_symbol: str = list_info[1].upper()

    # Use the obtained values as needed throgh API
    # API_CURRENCY_SYMBOL ALWAYS in USD
    api = CoinMktCap_API
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    params = {'symbol': crypto_symbol, 'convert': currency_symbol}
    headers = {'X-CMC_PRO_API_KEY': CoinMktCap_API}

    # session = Session()
    # session.headers.update(headers)

    # API request
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    last_updated = data['data'][crypto_symbol]['quote'][currency_symbol]['last_updated']
    current_price = data['data'][crypto_symbol]['quote'][currency_symbol]['price']

    print('Time fetched:', last_updated)
    print("Crypto Symbol:", crypto_symbol)
    print("Currency Symbol:", currency_symbol)
    print("Current Price at:", round(current_price,2))

    message.reply_text(f"Input received successfully.")
    message.reply_text(f"Time fetched: {last_updated} \nCrypto Symbol: {crypto_symbol} \nCurrency Symbol: {currency_symbol} \nCurrent Price: {round(current_price,2)}")
    # Clear the state to end the conversation
    context.user_data.pop('state')

    return ConversationHandler.END

# Our price_recurring_alert
def get_current_price(crypto_symbol, currency_symbol):
    api = CoinMktCap_API
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    params = {'symbol': crypto_symbol, 'convert': currency_symbol}
    headers = {'X-CMC_PRO_API_KEY': CoinMktCap_API}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    # last_updated = data['data'][crypto_symbol]['quote'][currency_symbol]['last_updated']
    current_price = data['data'][crypto_symbol]['quote'][currency_symbol]['price']
    return current_price


# From online for recurring
def price_recurring_Alert_command(update: Update, context: CallbackContext) -> None:
    if len(context.args) > 2:
        crypto = context.args[0].upper()
        sign = context.args[1]
        currency = context.args[2].upper()
        price = context.args[3]

        df = get_alert_input()
        update_alert_input(df, crypto, sign, currency, price)

        context.job_queue.run_repeating(priceAlertCallback, interval=15, first=15,
                                        context=[crypto, sign, currency, price, update.message.chat_id])
        response = f"⏳ I will send you a message when the price of {crypto} reaches {currency}{price}.\n"
        response += f"the current price of {crypto} is {currency}{round(get_current_price(crypto,currency),4)}"
    else:
        response = '⚠️ Please provide a crypto code and a price value: \nE.g.: /set_alert ETH < USD 2070' # means spot price < 2070

    context.bot.send_message(chat_id=update.effective_chat.id, text=response)

def get_alert_input():
    return alert_inputs

def update_alert_input(df, crypto, sign, currency, target_price):
    df.loc[len(alert_inputs.index)] = [crypto.upper(), sign, currency.upper(), target_price]
    print(df)

def priceAlertCallback(context):
    crypto = context.job.context[0].upper()
    sign = context.job.context[1]
    currency = context.job.context[2].upper()
    target_price = context.job.context[3]
    chat_id = context.job.context[4]

    send = False
    # gets current spot price
    spot_price = get_current_price(crypto, currency)

    # compare price that you set vs spot_price that you want
    if sign == '<':
        if float(spot_price) <= float(target_price):
            send = True
    elif sign == '>':
        if float(spot_price) >= float(target_price):
            send = True

    if send and sign == '<': # when crypto price is less than target price
        response = f'👋 {crypto} has went below {currency}{target_price} and has just reached {currency}{round(spot_price, 2)}!'

        context.job.schedule_removal()

        context.bot.send_message(chat_id=chat_id, text=response)

    elif send and sign == '>': # when crypto price is higher than target price
        response = f'👋 {crypto} has surpassed {currency}{target_price} and has just reached {currency}{round(spot_price, 2)}!'

        context.job.schedule_removal()

        context.bot.send_message(chat_id=chat_id, text=response)



# alert_inputs = {'Crypto_Symbol': [], '< / >': [], 'Currency':[], 'Price':[]}
def check_alert_command(update: Update, context: CallbackContext) -> None:
    if len(alert_inputs) == 0:
        update.message.reply_text("There are no price alerts in place.")
    else:
        update.message.reply_text("Here are the list of price alerts currently in place.")
        response = ""
        for index, rows in alert_inputs.iterrows():
            response += f"{index}.\t{rows['Crypto_Symbol']}\t{rows['< / >']}\t{rows['Currency']}\t{rows['Price']}\n"
        update.message.reply_text(response)


def current_price_for_alert(Crypto_Symbol, Currency):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    headers = {
        'X-CMC_PRO_API_KEY': '0e9e73ba-baa2-42e3-8f58-8217eeb1caee',
        'Accepts': 'application/json',
    }

    params = {
        'symbol': Crypto_Symbol,  # refers to bitcoin (highest market cap)
        'convert': Currency
    }
    data = requests.get(url, params=params, headers=headers).json()
    current_price = data['data'][Crypto_Symbol]['quote'][Currency]['price']
    return current_price


def remove_alert_command(update: Update, context: CallbackContext):
    df = get_alert_input()
    if len(df) == 0:
        update.message.reply_text("⚠️ There are no alerts to remove.")
    else:
        message: Message = update.message
        text = '⚠️ Please provide the number on the left: \nE.g.: 0. ETH > USD 2070\n Please input: 0'  # means spot price < 2070
        update.message.reply_text(text)

        context.user_data['state'] = CRYPTO_INPUT
        return CRYPTO_INPUT



def process_remove_alert_input(update: Update, context: CallbackContext) -> None:
    message: Message = update.message
    input_text = message.text
    # remove any white space from returned message
    index: int = int(input_text.strip())


    df = get_alert_input()
    if index >= len(df):
        update.message.reply_text(f'✘ Invalid input! Please try again.')

    else:
        df.drop(index, inplace=True)
        df.reset_index(drop=True, inplace=True)

        update.message.reply_text(f'Alert with number {index} has been removed! ✔')

    context.user_data.pop('state')
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it to the bot's token.
    updater = Updater('6488929133:AAGmDyAwvej_Th90qfEYGvdLU0uDE7GXgR8')

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler_current = ConversationHandler(
        entry_points=[CommandHandler('current_price', current_price_command)],
        states={
            CRYPTO_INPUT: [MessageHandler(Filters.text, process_crypto_input_current)]
        },
        fallbacks=[]
    )

    conv_handler_trade = ConversationHandler(
        entry_points=[CommandHandler('place_trade', place_trade_command)],
        states={
            CRYPTO_INPUT: [MessageHandler(Filters.text, process_crypto_input_trade)]
        },
        fallbacks=[]
    )

    conv_handler_remove_alert = ConversationHandler(
        entry_points=[CommandHandler('remove_alert', remove_alert_command)],
        states={
            CRYPTO_INPUT: [MessageHandler(Filters.text, process_remove_alert_input)]
        },
        fallbacks=[]
    )


    # Add the ConversationHandler to the dispatcher
    dispatcher.add_handler(CommandHandler('start', start)) # start command
    dispatcher.add_handler(CommandHandler('help', help_command)) # help command
    dispatcher.add_handler(CommandHandler('my_portfolio', portfolio_command)) # check portfolio holdings done
    dispatcher.add_handler(conv_handler_current) # get current price of certain crypto product
    dispatcher.add_handler(CommandHandler('set_alert', price_recurring_Alert_command))  # set alert
    dispatcher.add_handler(conv_handler_remove_alert)# remove alert
    dispatcher.add_handler(CommandHandler('check_alert', check_alert_command))  # check current alerts
    dispatcher.add_handler(conv_handler_trade) # place trade command
    dispatcher.add_handler(CommandHandler('exit', exit_command))

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()




# Look here for reference
# https://github.com/MWessels62/CryptoPricing_TelegramBot/blob/main/main.py
# https://www.youtube.com/watch?v=xNFK7toe5UE
# https://www.geeksforgeeks.org/get-real-time-crypto-price-using-python-and-binance-api/

# Telegram Update
if __name__ == '__main__':
    print('Starting ECON3086')
    main()
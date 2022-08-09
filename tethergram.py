import web3
import requests
import json
import os
from telegram import *
from telegram.ext import *

################## ETHEREUM INFO PROVIDER ##################
STATE1, STATE2, STATE3 = range(3)

class EtherAddressInfoProvider:
    def __init__(self):
        self.w3 = web3.Web3(
            web3.Web3.WebsocketProvider("wss://eth-mainnet.alchemyapi.io/v2/" + os.environ.get('ALCHEMY_API_KEY')))
        self.abi_endpoint = 'https://api.etherscan.io/api?module=contract&action=getabi&address='
        self.error = None

        # output
        self.addressData = {}
        self.contractData = {}
        self.blockData = None

    def get_eth_address_info(self, address: str):
        """
        https://web3py.readthedocs.io/en/latest/web3.eth.html
        """
        # Checksum Address mixes cases by using a specific pattern of upper and lowercase letters.
        # This is used to reduce the errors which might occur while typing or pasting the address.
        checkSumAddress = web3.Web3.toChecksumAddress(address)
        balance = self.w3.eth.get_balance(checkSumAddress)  # wei,1 Ether=10¹⁸ wei
        self.addressData['Balance'] = self.w3.fromWei(balance, 'ether')
        # Get tx = w3.eth.get_transaction() Returns the transaction specified by transaction_hash
        self.addressData['ENS_Name'] = self.w3.ens.name(checkSumAddress)
        self.addressData['Transaction_Count'] = self.w3.eth.get_transaction_count(checkSumAddress)
        self.get_contract_info(checkSumAddress)

    def get_contract_info(self, address):
        try:
            # Get abi
            response = requests.get('%s%s' % (self.abi_endpoint, address))
            response_json = response.json()

            if not 'NOTOK' in response_json['message']:
                abi = json.loads(response_json['result'])
                contract = self.w3.eth.contract(address=address, abi=abi)
                self.contractData["Name"] = contract.functions.name().call()
                self.contractData["Symbol"] = contract.functions.symbol().call()
                self.contractData["Owner"] = contract.functions.owner().call()
                dec = contract.functions.decimals().call()
                dec = 10 ** dec
                # Total supply
                self.contractData["Supply"] = contract.functions.totalSupply().call() / dec
            else:
                self.error = 1
        except:
            self.error = 1

    def get_block_info(self, block_height: int):
        if block_height:
            self.blockData = self.w3.eth.get_block(block_height)
        else:
            self.blockData = self.w3.eth.get_block('latest')

    def clear_data(self):
        self.contractData = {}
        self.addressData = {}
        self.blockData = {}

################## TELEGRAM BOT IMPLEMENTATION ##################
class TetherGram:
    def __init__(self):
        self.user = None
        self.heroku_token = os.environ.get('HEROKU_TOKEN')
        self.updater = Updater(self.heroku_token, use_context=True)
        self.address_provider = EtherAddressInfoProvider()
        self.state = 0

    def main_menu(self, update: Update, context: CallbackContext):
        self.state = 0
        self.user = update.effective_chat.username
        keyboard = [[InlineKeyboardButton('Query information of an ETH address', callback_data="QUERY")],
                    [InlineKeyboardButton('Set up an alert for an ETH address', callback_data="ALERT")],
                    [InlineKeyboardButton('Exit', callback_data="EXIT")]]
        text = "Welcome " + self.user + "! With Tethergram you are able to query " \
               "information from the Ethereum network or set up a change " \
               "alert for any Ethereum address. Tethergram is created by the WolfBrothers.\n"

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))

    def ethereum_address_query_menu(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        self.state = 1
        keyboard = [[InlineKeyboardButton("Return to main menu", callback_data="BACK")]]
        text = "Query information of the Ethereum network. You need to enter an Ethereum address which " \
                "will be analyzed and given back public information. \n"
        query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard))

    def ethereum_address_alert_menu(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        self.state = 2
        text = "Sorry, this function not implemented yet!"
        keyboard = [[InlineKeyboardButton("Return to main menu", callback_data="BACK")]]

        query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard))

    def text_handler(self, update: Update, context: CallbackContext):
        if self.state == 0:
            user_message = str(update.message.text)
            update.message.reply_text(text=user_message)
        elif self.state == 1:
            user_message = str(update.message.text)
            if not self.address_provider.w3.isAddress(user_message):
                update.message.reply_text(text=f'Bad Ethereum address format! Please re-enter the Ethereum address')
                return

            self.address_provider.clear_data()
            update.message.reply_text(text=f'Entered ETH address: {user_message}')
            update.message.reply_text(text=f'Fetching Ethereum address data, please wait...')
            self.address_provider.get_eth_address_info(user_message)
            text_data = ""
            if len(self.address_provider.addressData) != 0:
                text_data += "Ethereum address base information: " + '\n'
                for key in self.address_provider.addressData:
                    text_data += str(key) + ": " + str(self.address_provider.addressData[key]) + '\n'

            if len(self.address_provider.contractData) != 0:
                text_data += "The address is a smart contract. Additional contract information:" + '\n'
                for key in self.address_provider.contractData:
                    text_data += str(key) + ": " + str(self.address_provider.contractData[key]) + '\n'
            else:
                text_data += "The address is not a smart contract."

            update.message.reply_text(text=text_data)
        else:
            update.message.reply_text(
                text=f'Sorry, this function is not implemented yet! Please return to the main menu!')

    def end_session(self, update: Update, context: CallbackContext):
        self.user = update.effective_chat.username
        text = "Good bye " + self.user + "!\n"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        return ConversationHandler.END

    def help(self, update: Update, context: CallbackContext):
        text = "Ethereum info provider by the WolfBrothers. You can use the following commands to take action: \n" \
               "/start - restart the session\n" \
               "/help  - list the actions which you can do with this bot \n" \
               "/exit  - end telegram bot session\n"
        update.message.reply_text(text)

    def main(self):
        dispatcher = self.updater.dispatcher

        dispatcher.add_handler(CommandHandler('start', self.main_menu))
        dispatcher.add_handler(CommandHandler('help', self.help))
        dispatcher.add_handler(CommandHandler('exit', self.end_session))

        dispatcher.add_handler(CallbackQueryHandler(self.ethereum_address_query_menu, pattern="QUERY"))
        dispatcher.add_handler(CallbackQueryHandler(self.ethereum_address_alert_menu, pattern="ALERT"))
        dispatcher.add_handler(CallbackQueryHandler(self.end_session, pattern="EXIT"))
        dispatcher.add_handler(CallbackQueryHandler(self.main_menu, pattern="BACK"))

        dispatcher.add_handler(MessageHandler(Filters.text, self.text_handler, run_async=True))

        self.updater.start_webhook(listen="0.0.0.0",
                                           port=int(os.environ.get('PORT', 8443)),
                                           url_path=self.heroku_token,
                                           webhook_url='https://hidden-scrubland-39900.herokuapp.com/' + self.heroku_token)
        self.updater.idle()

if __name__ == '__main__':
    tethergrambot = TetherGram()
    tethergrambot.main()
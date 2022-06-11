import web3
import json
import requests
import logging
import os
from decouple import config
from telegram import *
from telegram.ext import Updater, CommandHandler, CallbackContext, \
    MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


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
        self.addressData['EnsName'] = self.w3.ens.name(checkSumAddress)
        self.addressData['TxCount'] = self.w3.eth.get_transaction_count(checkSumAddress)
        #self.get_contract_info(checkSumAddress)

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


class TEtherBot:
    def __init__(self):
        self.heroku_token = os.environ.get('HEROKU_TOKEN')
        self.updater = Updater(self.heroku_token, use_context=True)
        self.address_provider = EtherAddressInfoProvider()

    def start(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text(text='Welcome to Ethereum address scraper!\nPlease provide an Ethereum address!')

    def help(self, update, context):
        """Send a message when the command /help is issued."""
        update.message.reply_text('Help!')

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def textHandler(self, update: Update, context: CallbackContext) -> None:
        user_message = str(update.message.text)
        if not self.address_provider.w3.isAddress(user_message):
            logger.warning('Bad Ethereum address was given: "%s"', )
            return

        update.message.reply_text(text=f'Entered ETH address: {user_message}')
        update.message.reply_text(text=f'Fetching Ethereum address data, please wait...')
        self.address_provider.get_eth_address_info(user_message)
        update.message.reply_text(text=f'Address balance: '
                                       f'{self.address_provider.addressData["Balance"]}')
        update.message.reply_text(text=f'Address ENS name: '
                                       f'{self.address_provider.addressData["EnsName"]}')
        update.message.reply_text(text=f'Address tx count: '
                                       f'{self.address_provider.addressData["TxCount"]}')
    def main(self):
        self.updater.dispatcher.add_handler(CommandHandler('start', self.start))
        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.all & ~Filters.command, self.textHandler, run_async=True))
        self.updater.dispatcher.add_handler(CommandHandler("help", help))

        self.updater.start_webhook(listen="0.0.0.0",
                                   port=int(os.environ.get('PORT', 8443)),
                                   url_path=self.heroku_token,
                                   webhook_url='https://hidden-scrubland-39900.herokuapp.com/' + self.heroku_token)
        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        self.updater.idle()


if __name__ == '__main__':
    tetherbot = TEtherBot()
    tetherbot.main()

# Example addresses
# 0xbab815e5d14160140f2ae08d04c14571dfeddc7c
# 0xB5dFA399Dc4a3BfEB196395746f82fA089D788E1

import socket
import subprocess

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.stacklayout import StackLayout
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp
from kivy.lang import Builder
from kivy.core.window import Window
from paypal import *
import random
from csv import writer
import pandas as pd
from datetime import datetime
import time
import string
from barcode import EAN13
from barcode.writer import ImageWriter
from uuid import uuid4

import threading

SCAN_TIME = 5
Window.size = (300, 500)  # for mobile phones only

send_cond = False
recv_cond = False

pay_amount = 0.00 #amount generated in the phone
paid_amount = 0.00 #amount confirmed with payment gateway by the terminal
client_data = ''
pot_selected = 'None'
loyaltyname = 'None'
loyaltycode = 111111111111
unsorted = 0

TERMINAL_IP = socket.gethostbyname(socket.gethostname())
PORT_NUMBER = 5005
SIZE = 1024


def sender():
    global client_data, send_cond
    while True:
        try:
            while send_cond:
                send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                send_socket.connect((TERMINAL_IP, PORT_NUMBER))
                print('connect')
                while True:
                    if client_data != '':
                        send_socket.send(bytes(client_data, 'utf-8'))
                        client_data = ''
        except:
            time.sleep(0.5)


thread_1 = threading.Thread(target=sender)


def receiver():
    global paid_amount, recv_cond

    while recv_cond:
        try:
            recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            recv_socket.bind((TERMINAL_IP, PORT_NUMBER))
            recv_socket.listen(10)
            print('binded')
            while True:
                listen_socket, address = recv_socket.accept()
                while True:
                    raw_msg = listen_socket.recv(1024)
                    paid_amount = raw_msg.decode('utf-8')
        except:
            time.sleep(0.5)
            print('binding...')


thread_2 = threading.Thread(target=receiver)


class WindowManager(MDScreenManager):
    pass


class LoadScreen(MDScreen):
    pass


class HomeScreen(MDScreen):

    #pay_amount = str(round(random.uniform(0.00, 9.99), 2))

    def read_pots(self):
        self.pots = pd.read_csv("pots.csv")
        self.pot_names = list(self.pots['Name'])
        self.pot_limits = list(self.pots['Limit'])
        self.pot_rems = list(self.pots["Balance"])

    pot_selected = "None"

    pot_layout = StackLayout()

    def get_amount(self):
        global pay_amount
        new_amount = "%.2f" % round(random.uniform(0.00, 9.99), 2)  # keeps 2 decimal points with trailing zeros
        pay_amount = new_amount
        self.ids.amount.text = "Amount: " + pay_amount + " GBP"
        self.manager.ids.justpayscreen.ids.paynow.disabled = False
        self.manager.ids.potpayscreen.ids.confirm.disabled = False
        self.manager.ids.potpayscreen.ids.potname.text = "None"
        self.manager.ids.potpaidscreen.ids.potname.text = "None"
        self.ids.justpay.disabled = False
        self.ids.loyalty.disabled = False
        self.clear_pots()
        self.manager.ids.loyaltyscreen.clear_loyalty()

    def load_home(self):
        global unsorted
        self.read_pots()
        self.transactions = pd.read_csv("transactions.csv")
        unsorted = self.transactions[self.transactions["pot"] == "None"].shape[0]
        self.ids.sort.text = f"Sort({unsorted})"
        for name in self.pot_names:
            button = MDRaisedButton(id=name, text=name)
            button.bind(on_release=lambda btn=name: self.button_press(btn))
            button.disabled = False
            self.pot_layout.add_widget(button)
        self.add_widget(self.pot_layout)

    def button_press(self, btn):
        global pay_amount, pot_selected, unsorted
        self.read_pots()
        pot_selected = btn.text
        self.manager.current = 'potpay'
        self.manager.ids.potpayscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.potpayscreen.ids.amount.text = "Amount: " + str(pay_amount) + " GBP"
        self.manager.ids.justpayscreen.ids.amount.text = "Amount: " + str(pay_amount) + " GBP"
        self.manager.ids.potpayscreen.ids.potname.text = btn.text
        self.manager.ids.potpaidscreen.ids.potname.text = btn.text
        pot_limit = str(self.pots[self.pots["Name"] == btn.text]["Limit"].values[0])
        self.manager.ids.potpayscreen.ids.potlimit.text = "Limit\n" + str(round(float(pot_limit), 2))
        self.manager.ids.potpaidscreen.ids.potlimit.text = "Limit\n" + str(round(float(pot_limit), 2))
        pot_balance = str(self.pots[self.pots["Name"] == btn.text]["Balance"].values[0])
        self.manager.ids.potpayscreen.ids.potrem.text = "Balance\n" + str(round(float(pot_balance), 2))
        self.manager.ids.potpaidscreen.ids.potrem.text = "Balance\n" + str(round(float(pot_balance), 2))
        self.clear_pots()
        btn.disabled = True
        return btn.text

    def clear_pots(self):
        self.read_pots()
        try:
            for i in range(len(self.pot_names)):
                self.pot_layout.children[i].disabled = False
        except:
            pass

    def disable_pots(self):
        self.read_pots()
        try:
            for i in range(len(self.pot_names)):
                self.pot_layout.children[i].disabled = True
        except:
            pass


class JustPayScreen(MDScreen):
    pots = pd.read_csv("pots.csv")

    def read_transactions(self):
        self.transactions = pd.read_csv("transactions.csv")
        self.cols = self.transactions.columns.values
        self.values = self.transactions.values.tolist()

    def just_pay(self, btn):
        global pay_amount, paid_amount
        self.send_pay()
        self.record_pay()
        self.pay()
        btn.disabled = True
        self.manager.current = 'home'
        self.manager.ids.justpayscreen.ids.amount.text = "Amount: " + str(pay_amount) + " GBP"
        self.manager.ids.homescreen.ids.justpay.disabled = True
        self.manager.ids.homescreen.ids.loyalty.disabled = True
        self.manager.ids.potpayscreen.ids.confirm.disabled = True
        self.manager.ids.homescreen.disable_pots()

    def pay(self):
        global paid_amount, pay_amount, client_data
        client_id = client_data[:80]
        client_secret = client_data[80:]

        letters = string.ascii_lowercase
        batch_code = "".join(random.choice(letters) for i in range(200))
        #batch_code = '123' #inorder to make the payment fail
        response = make_payment(client_id, client_secret, pay_amount, batch_code)

        # Check the response to see if the payment was successful
        if response.status_code == 201:
            response_text = "Payment sent successfully!"
        else:
            response_text = f"Payment failed: {response.status_code}"

        close_button = MDFlatButton(text="Close", on_release=self.close_pay)

        self.dialog_pay = MDDialog(title="Payment status",
                               text=response_text,
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog_pay.open()

    def record_pay(self):
        global pay_amount, client_data, pot_selected, loyaltycode, unsorted
        self.transactions = pd.read_csv("transactions.csv")
        now = datetime.now()
        dt_string = now.strftime("%Y%m%d %H:%M:%S")
        id = str(int(dt_string[:8] + dt_string[9:11] + dt_string[12:14] + dt_string[-2:]))
        try:
            data_entry = [id, pay_amount, pot_selected, loyaltycode, dt_string]
            with open('transactions.csv', 'a', newline='') as file:
                writer_object = writer(file)
                writer_object.writerow(data_entry)
                file.close()
            if pot_selected != "None":
                check_string = "Transaction added successfully.\n Spent " + pay_amount + " GBP\n from " + pot_selected + " Pot."
                self.pots.loc[self.pots['Name'] == pot_selected, 'Balance'] -= float(pay_amount)
                self.pots.to_csv('pots.csv', index=False)
                pot_limit = str(self.pots[self.pots["Name"] == pot_selected]["Limit"].values[0])
                self.manager.ids.potpaidscreen.ids.potlimit.text = "Limit\n" + str(round(float(pot_limit), 2))
                pot_balance = str(self.pots[self.pots["Name"] == pot_selected]["Balance"].values[0])
                self.manager.ids.potpaidscreen.ids.potrem.text = "Balance\n" + str(round(float(pot_balance), 2))
            else:
                check_string = "Transaction added successfully.\n Spent " + pay_amount + " GBP\n without choosing a pot"
        except:
            check_string = "Failed to update the transaction."

        unsorted = self.transactions[self.transactions["pot"] == "None"].shape[0]

        close_button = MDFlatButton(text="Close", on_release=self.close_record,
                                    pos_hint={'center_x': 0.2})
        sort_button = MDRaisedButton(text=f"Sort ({unsorted}) ", on_release=self.goto_sort,
                                     pos_hint={'center_x': 0.8})

        self.dialog_record = MDDialog(title="Payment status",
                               #text=response_text+"\n"+check_string,
                               text = check_string,
                               size_hint=(0.7, 1), buttons=[close_button, sort_button])
        self.dialog_record.open()

    def send_pay(self):
        global client_data
        # Set up your PayPal API credentials
        client_id = "AfODQAuk-f-Ait4OKTHweC-hBhqIQXVkDaDDOgnrn8uNG9pS_tO9kfG71mevAyvIRKiLsD5d5KyMoZ09"
        client_secret = "EO0NHZ2yztKGLMcvEFLZw7dapQHHk6CKDfA2gYGw6aGK3rYNc7IbzgINrn8xbPEIcGJtl-ux7UXBvjLI"
        client_data = client_id+client_secret

    def close_record(self, obj):
        self.dialog_record.dismiss()

    def goto_sort(self, obj):
        self.manager.current = 'sort'
        self.manager.ids.sortscreen.show_table()
        self.dialog_record.dismiss()

    def close_pay(self, obj):
        self.dialog_pay.dismiss()


class PotPayScreen(MDScreen):

    def confirm_pay(self, btn):
        self.manager.current = 'potpaid'
        self.manager.ids.justpayscreen.send_pay()
        self.manager.ids.justpayscreen.pay()
        self.manager.ids.justpayscreen.record_pay()
        btn.disabled = True
        self.manager.ids.homescreen.ids.justpay.disabled = True
        self.manager.ids.homescreen.ids.loyalty.disabled = True
        self.manager.ids.justpayscreen.ids.paynow.disabled = True
        self.manager.ids.homescreen.disable_pots()


class PotPaidScreen(MDScreen):
    pass


class LoyaltyScreen(MDScreen):

    loyalty_layout = StackLayout()

    def read_loyalty(self):
        self.loyalty = pd.read_csv("loyalty.csv")
        self.loyalty_names = list(self.loyalty['Name'])
        self.loyalty_codes = list(self.loyalty['Code'])

    def clear_loyalty(self):
        try:
            for i in range(len(self.loyalty_names)):
                self.loyalty_layout.children[i].disabled = False
        except:
            pass

    def save_barcode(self, name, code):
        barcode = EAN13(code, writer=ImageWriter())
        barcode.save(name)

    def load_loyalty(self):
        self.read_loyalty()
        for name in self.loyalty_names:
            button = MDRaisedButton(id=name, text=name)
            button.bind(on_release=lambda btn=name: self.button_press(btn))
            button.disabled = False
            self.loyalty_layout.add_widget(button)
        self.add_widget(self.loyalty_layout)

    def button_press(self, btn):
        global loyaltycode
        self.read_loyalty()
        self.manager.current = 'scan'
        self.manager.ids.scanscreen.ids.loyaltyname.text = btn.text + ' card'
        loyalty_code = str(int(self.loyalty[self.loyalty["Name"] == btn.text]["Code"].values[0]))
        self.save_barcode(btn.text, loyalty_code)
        self.manager.ids.scanscreen.ids.loyaltybarcode.source = btn.text+'.png'
        self.clear_loyalty()
        btn.disabled = True
        return btn.text


class ScanScreen(MDScreen):

    def read_loyalty(self):
        self.loyalty = pd.read_csv("loyalty.csv")
        self.loyalty_names = list(self.loyalty['Name'])
        self.loyalty_codes = list(self.loyalty['Code'])

    def scan_loyalty(self):
        self.read_loyalty()
        self.manager.ids.homescreen.ids.loyalty.disabled = True
        time.sleep(SCAN_TIME)
        self.manager.current = 'home'


class ShowScreen(MDScreen):

    def read_transactions(self):
        self.transactions = pd.read_csv("transactions.csv")
        self.cols = self.transactions.columns.values
        self.values = self.transactions.values.tolist()

    def load_table(self):
        self.read_transactions()
        layout = MDBoxLayout(orientation='vertical', spacing=0.01 * self.height)
        column_data = [(col, dp(10)) for col in self.cols]
        row_data = self.values
        self.table = MDDataTable(column_data=column_data, row_data=row_data, rows_num=100,
                                 size_hint=(0.9, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.button = MDFlatButton(text="Home", on_press=self.close_table)
        self.add_widget(self.table)
        self.add_widget(self.button)
        return layout

    def show_table(self):
        self.load_table()
        print(self.manager.current)

    def close_table(self, obj):
        self.manager.current = 'home'


class ShowPotsScreen(MDScreen):

    def read_pots(self):
        self.pots = pd.read_csv("pots.csv")
        self.cols = self.pots.columns.values
        self.values = self.pots.values.tolist()

    def load_table(self):
        self.read_pots()
        layout = MDBoxLayout(orientation='vertical', spacing=0.01 * self.height)
        column_data = [(col, dp(15)) for col in self.cols]
        row_data = self.values
        self.table = MDDataTable(column_data=column_data, row_data=row_data,
                                 rows_num=100, size_hint=(0.9, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.button1 = MDFlatButton(text="Add a new pot", on_press=self.create_pot,
                                    pos_hint={'center_x': 0.2})
        self.button2 = MDFlatButton(text="Cancel", on_press=self.close_table,
                                    pos_hint={'center_x': 0.8})
        self.add_widget(self.table)
        self.add_widget(self.button1)
        self.add_widget(self.button2)
        return layout

    def show_table(self):
        self.load_table()

    def create_pot(self, obj):
        self.manager.current = 'newpot'

    def close_table(self, obj):
        self.manager.current = 'home'


class ShowNewScreen(MDScreen):
    pass


class SortScreen(MDScreen):
    selected_row_id = None
    num_cols = 5

    def read_pots(self):
        self.pots = pd.read_csv("pots.csv")
        self.pot_names = list(self.pots['Name'])

    def get_transactions(self):
        self.transactions = pd.read_csv("transactions.csv")
        self.unsorted = self.transactions[self.transactions["pot"] == "None"]
        self.cols = self.unsorted.columns.values
        self.num_cols = len(self.cols)
        self.values = self.transactions.values.tolist()
        self.unsorted_values = self.unsorted.values.tolist()

    def load_table(self):
        self.get_transactions()
        layout = MDBoxLayout(orientation='vertical', spacing=0.01*self.height)
        #layout = AnchorLayout()
        column_data = [(col, dp(10)) for col in self.cols]
        row_data = self.unsorted_values
        self.unsorted_table = MDDataTable(column_data=column_data, row_data=row_data, rows_num=100, check=True,
                                          size_hint=(0.9, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.unsorted_table.bind(on_row_press=self.on_row_press)
        self.unsorted_table.bind(on_check_press=self.on_check_press)
        self.add_widget(self.unsorted_table)
        self.button = MDFlatButton(text="Home", on_press=self.close_table)
        self.add_widget(self.button)
        return layout

    def show_table(self):
        self.load_table()

    def close_table(self, obj):
        self.manager.current = 'home'

    def on_row_press(self, instance_table, instance_row):
        self.read_pots()
        self.selected_row_id = instance_row.table.row_data[instance_row.index//self.num_cols][self.num_cols-1]
        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)
        buttons = []
        for pot in self.pot_names:
            buttons.append(MDFlatButton(text=pot, on_release=self.assign_pot))
        buttons.append(close_button)
        i = 0
        buttons_list = []
        while i < len(buttons):
            buttons_list.append(buttons[i:i + 3]) # to create a nested list with 3 item lists
            i += 3

        self.dialog = MDDialog(title="Assign a pot",
                               text="Please choose a pot to assign to the selected transaction",
                               size_hint=(1, 0.5), buttons=buttons, type="simple")
        self.dialog.open()

    def assign_pot(self, instance):
        global unsorted
        self.transactions.loc[self.transactions['timestamp'] == self.selected_row_id, 'pot'] = instance.text
        self.transactions.to_csv('transactions.csv', index=False)
        self.get_transactions()
        unsorted = self.transactions[self.transactions["pot"] == "None"].shape[0]

    def close_dialog(self, obj):
        self.dialog.dismiss()
        self.show_table()

    def on_check_press(self, instance_table, current_row):
        print(current_row)


class NewPotScreen(MDScreen):

    pot_layout = StackLayout()

    def read_pots(self):
        self.pots = pd.read_csv("pots.csv")
        self.pot_names = list(self.pots['Name'])
        self.pot_limits = list(self.pots['Limit'])
        self.pot_rems = list(self.pots["Balance"])

    def load_new_pot(self, newpot):
        self.read_pots()
        if newpot in self.pot_names:
            button = MDRaisedButton(id=newpot, text=newpot)
            button.bind(on_release=lambda btn=newpot: self.button_press(btn))
            button.disabled = False
            self.pot_layout.add_widget(button)

    def add_pot(self, pot_name, pot_limit):
        if pot_limit == '':
            check_string = f'Pot limit is empty!'
        else:
            try:
                data_entry = [pot_name, pot_limit, pot_limit]
                with open('pots.csv', 'a') as file:
                    writer_object = writer(file)
                    writer_object.writerow(data_entry)
                    file.close()
                check_string = f"{pot_name} pot added with a limit of {pot_limit} GBP successfully"
            except:
                check_string = "Failed to add the pot"

        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)

        self.dialog = MDDialog(title="Adding a new pot",
                               text= check_string,
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def close_dialog(self, obj):
        self.dialog.dismiss()


class NewLoyaltyScreen(MDScreen):
    loyalty_layout = StackLayout()

    def read_loyalty(self):
        self.loyalty = pd.read_csv("loyalty.csv")
        self.loyalty_names = list(self.loyalty['Name'])
        self.loyalty_codes = list(self.loyalty['Code'])

    def load_new_loyalty(self, new):
        self.read_loyalty()
        if new in self.loyalty_names:
            button = MDRaisedButton(id=new, text=new)
            button.bind(on_release=lambda btn=new: self.button_press(btn))
            button.disabled = False
            self.loyalty_layout.add_widget(button)

    def add_loyalty(self, loyalty_name, loyalty_code):
        if len(loyalty_code) != 12:
            check_string = "Invalid loyalty code!"
        else:
            try:
                data_entry = [loyalty_name, loyalty_code]
                with open('loyalty.csv', 'a', newline='') as file:
                    writer_object = writer(file)
                    writer_object.writerow(data_entry)
                    file.close()
                check_string = f"{loyalty_name} loyalty card added successfully"
            except:
                check_string = "Failed to add the loyalty card"
                self.ids.confirm.disabled = True

        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)

        self.dialog = MDDialog(title="Adding a new loyalty card",
                               text= check_string,
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def close_dialog(self, obj):
        self.dialog.dismiss()


class DemoApp(MDApp):
    def build(self):
        self.transactions = pd.read_csv("transactions.csv")
        self.unsorted = self.transactions[self.transactions["pot"] == "None"].shape[0]
        self.theme_cls.primary_palette = "Cyan"
        self.theme_cls.primary_hue = "900"
        self.theme_cls.theme_style = "Light"

        kv = Builder.load_file("helper.kv")
        return kv


if __name__ == "__main__":
    DemoApp().run()

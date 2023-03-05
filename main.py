import socket
import subprocess
import sqlite3
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
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
import pygal
import matplotlib.pyplot as plt
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg

SCAN_TIME = 5
Window.size = (300, 500)  # for mobile phones only

send_cond = False
recv_cond = False

pay_amount = 0.00  # amount generated in the phone
paid_amount = 0.00  # amount confirmed with payment gateway by the terminal
client_data = ''
pot_selected = 'None'
loyalty_name = 'None'
loyalty_code = 111111111111
unsorted = 0
pots = pd.DataFrame()
trans = pd.DataFrame()
loyalty = pd.DataFrame()
clients = pd.DataFrame()

loyalty_names = []
pot_names = []
user_name = ''

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


class SignInScreen(MDScreen):
    def signin(self, username):
        global clients, client_data, user_name

        clients = pd.read_csv('users.csv')
        usernames = clients['username'].tolist()

        if username in usernames:
            client_data = clients[clients['username'] == username]['client_id'].values[0] + \
                          clients[clients['username'] == username]['client_secret'].values[0]
            self.manager.current = 'home'
            user_name = username
            self.manager.ids.homescreen.load_home()
            self.manager.ids.loyaltyscreen.load_loyalty()
        else:
            self.button = MDFlatButton(text='Try again', on_release=self.retry, pos_hint={'center_x': 0.5})
            self.dialog = MDDialog(title="SignIn status", text='Invalid username',
                                   size_hint=(0.7, 1), buttons=[self.button])
            self.dialog.open()

    def retry(self, obj):
        self.dialog.dismiss()
        self.ids.username.text = ''


class SignUpScreen(MDScreen):
    pass


class HomeScreen(MDScreen):

    pot_layout = StackLayout()

    def get_amount(self):
        global pay_amount, pot_selected
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
        pot_selected = 'None'

    def load_home(self):
        global unsorted, pots, trans, pot_names, user_name
        all_pots = pd.read_csv("pots.csv")
        pots = all_pots[all_pots['username'] == user_name]
        pot_names = list(pots['Name'])

        all_trans = pd.read_csv("transactions.csv")
        trans = all_trans[all_trans['username'] == user_name]

        #pots.sort_values(by='Weight', ascending=False, inplace=True)
        unsorted = trans[trans["pot"] == "None"].shape[0]
        self.update_sort_buttons()

        for name in pot_names:
            usage = pots[pots["Name"] == name]["Usage"].values[0]
            weight = int(pots[pots["Name"] == name]["Weight"].values[0])
            button = MDRaisedButton(id=name, text=f'{name}-{usage} ({weight})')
            button.bind(on_release=lambda btn=name: self.button_press(btn))
            button.disabled = True
            self.pot_layout.add_widget(button)
        self.add_widget(self.pot_layout)

    def unload_home(self):
        try:
            while True: #as long as there are buttons in the layout
                self.pot_layout.remove_widget(self.pot_layout.children[0])
        except:
            pass
        self.remove_widget(self.pot_layout)

    def button_press(self, btn):
        global pay_amount, pot_selected, unsorted, pots
        pot_selected = btn.id
        self.manager.current = 'potpay'
        self.manager.ids.potpayscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.potpayscreen.ids.amount.text = "Amount: " + str(pay_amount) + " GBP"
        self.manager.ids.justpayscreen.ids.amount.text = "Amount: " + str(pay_amount) + " GBP"
        self.manager.ids.potpayscreen.ids.potname.text = btn.text
        self.manager.ids.potpaidscreen.ids.potname.text = btn.text
        pot_limit = str(pots[pots["Name"] == btn.id]["Limit"].values[0])
        self.manager.ids.potpayscreen.ids.potlimit.text = "Limit\n" + str(round(float(pot_limit), 2))
        self.manager.ids.potpaidscreen.ids.potlimit.text = "Limit\n" + str(round(float(pot_limit), 2))
        pot_balance = str(pots[pots["Name"] == btn.id]["Balance"].values[0])
        self.manager.ids.potpayscreen.ids.potrem.text = "Balance\n" + str(round(float(pot_balance), 2))
        self.manager.ids.potpaidscreen.ids.potrem.text = "Balance\n" + str(round(float(pot_balance), 2))
        self.clear_pots()
        btn.disabled = True
        return btn.text

    def update_pot_buttons(self):
        global pots, pot_names, trans, user_name
        all_trans = pd.read_csv("transactions.csv")
        trans = all_trans[all_trans['username'] == user_name]
        #pots.sort_values(by='Weight', ascending=False, inplace=True)
        for i, name in enumerate(pot_names):
            trans_spend = trans.groupby('pot').agg({'amount': ['sum', 'count']})
            pot_spend = trans_spend.loc[name][0]
            pot_weight = trans_spend.loc[name][1]
            pot_limit = pots[pots['Name']==name]['Limit'].values[0]
            pots.loc[pots['Name'] == name, 'Balance'] = pot_limit - pot_spend
            pots.loc[pots['Name']==name, 'Usage'] = '{:.0%}'.format(round(float(pot_spend)/float(pot_limit), 2))
            pots.loc[pots['Name'] == name, 'Weight'] = int(pot_weight)
            pot_usage = pots[pots["Name"]==name]["Usage"].values[0]
            pot_weight = int(pots[pots["Name"]==name]["Weight"].values[0])
            self.pot_layout.children[i].text = f'{name}-{pot_usage} ({pot_weight})'
        all_pots = pd.read_csv('pots.csv')
        other_pots = all_pots[all_pots['username'] != user_name]
        all_pots = pots.append(other_pots)
        all_pots.to_csv('pots.csv', index=False)

    def update_sort_buttons(self):
        global unsorted
        self.ids.sort.text = f'Sort({unsorted})'
        self.manager.ids.loyaltyscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.justpayscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.potpayscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.potpaidscreen.ids.sort.text = f"Sort({unsorted})"

    def clear_pots(self):
        global pots, pot_names
        try:
            for i in range(len(pot_names)):
                self.pot_layout.children[i].disabled = False
        except:
            pass

    def disable_pots(self):
        global pots, pot_names
        try:
            for i in range(len(pot_names)):
                self.pot_layout.children[i].disabled = True
        except:
            pass


class JustPayScreen(MDScreen):

    def pay_now(self, btn):
        global pay_amount, paid_amount
        #self.send_pay()
        if self.pay():
            paid_amount = pay_amount
            self.record_pay()
            #btn.disabled = True
            self.manager.current = 'home'
            self.manager.ids.justpayscreen.ids.amount.text = "Amount: " + str(paid_amount) + " GBP"
            self.manager.ids.homescreen.ids.justpay.disabled = True
            self.manager.ids.homescreen.ids.loyalty.disabled = True
            self.manager.ids.potpayscreen.ids.confirm.disabled = True
            self.manager.ids.homescreen.disable_pots()
            pay_amount = 0.00
            self.manager.ids.homescreen.ids.amount.text = "Amount: " + str(pay_amount) + " GBP"
            self.manager.ids.homescreen.update_sort_buttons()

    def pay(self):
        global paid_amount, pay_amount, client_data
        payment_success = False
        client_id = client_data[:80]
        client_secret = client_data[80:]

        letters = string.ascii_lowercase
        batch_code = "".join(random.choice(letters) for i in range(200))
        #batch_code = '123' #inorder to make the payment fail
        response = make_payment(client_id, client_secret, pay_amount, batch_code)

        # Check the response to see if the payment was successful
        if response is None:
            response_text = "Payment failed without a response"
        elif response.status_code == 201:
            response_text = "Payment sent successfully!"
            payment_success = True
        else:
            response_text = f"Payment failed: {response.status_code}"

        close_button = MDFlatButton(text="Close", on_release=self.close_pay)

        self.dialog_pay = MDDialog(title="Payment status",
                               text=response_text,
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog_pay.open()

        return payment_success

    def record_pay(self):
        global pay_amount, client_data, pot_selected, loyalty_code, unsorted, trans, pots, user_name
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        #id = str(int(dt_string[:4] + dt_string[5:7] + dt_string[8:10] + dt_string[11:13]+ dt_string[14:16]+dt_string[-2:]))
        lower = string.ascii_lowercase
        upper = string.ascii_uppercase
        numbers = '0123456789'
        all = lower + upper + numbers
        id = "".join(random.choice(all) for i in range(10))
        try:
            data_entry = [id, pay_amount, pot_selected, loyalty_code, dt_string, user_name]
            with open('transactions.csv', 'a', newline='') as file:
                writer_object = writer(file)
                writer_object.writerow(data_entry)
                file.close()
            if pot_selected != "None":
                check_string = "Transaction added successfully.\n Spent " + pay_amount + " GBP\n from " + pot_selected + " Pot."
                pots.loc[pots['Name'] == pot_selected, 'Balance'] -= float(pay_amount)
                pots.loc[pots['Name'] == pot_selected, 'Weight'] += 1
                pot_limit = str(pots[pots["Name"] == pot_selected]["Limit"].values[0])
                self.manager.ids.potpaidscreen.ids.potlimit.text = "Limit\n" + str(round(float(pot_limit), 2))
                pot_balance = str(pots[pots["Name"] == pot_selected]["Balance"].values[0])
                self.manager.ids.potpaidscreen.ids.potrem.text = "Balance\n" + str(round(float(pot_balance), 2))
                pots.loc[pots['Name'] == pot_selected, 'Usage'] = '{:.0%}'.format(round((float(pot_limit)-float(pot_balance))/float(pot_limit),2))
                usage = pots[pots["Name"] == pot_selected]["Usage"].values[0]
                weight = int(pots[pots["Name"] == pot_selected]["Weight"].values[0])
                self.manager.ids.potpaidscreen.ids.potname.text = f'{pot_selected}-{usage} ({weight})'
            else:
                check_string = "Transaction added successfully.\n Spent " + pay_amount + " GBP\n without choosing a pot"
        except:
            check_string = "Failed to update the transaction."
        all_pots = pd.read_csv('pots.csv')
        other_pots = all_pots[all_pots['username'] != user_name]
        all_pots = pots.append(other_pots)
        all_pots.to_csv('pots.csv', index=False)
        self.manager.ids.homescreen.update_pot_buttons()

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
        global pay_amount, paid_amount
        self.manager.current = 'potpaid'
        #self.manager.ids.justpayscreen.send_pay()
        if self.manager.ids.justpayscreen.pay():
            paid_amount = pay_amount
            self.manager.ids.justpayscreen.record_pay()
            #btn.disabled = True
            #self.manager.ids.potpaidscreen.amount.text = "Amount: " + str(paid_amount) + " GBP"
            self.manager.ids.homescreen.ids.justpay.disabled = True
            self.manager.ids.homescreen.ids.loyalty.disabled = True
            self.manager.ids.justpayscreen.ids.paynow.disabled = True
            self.manager.ids.homescreen.disable_pots()
            pay_amount = 0.00
            self.manager.ids.homescreen.ids.amount.text = "Amount: " + str(pay_amount) + " GBP"


class PotPaidScreen(MDScreen):
    pass


class LoyaltyScreen(MDScreen):

    loyalty_layout = StackLayout()

    def read_loyalty(self):
        global loyalty, loyalty_names, user_name
        all_loyalty = pd.read_csv("loyalty.csv")
        loyalty = all_loyalty[all_loyalty['username'] == user_name]
        loyalty_names = list(loyalty['Name'])

    def clear_loyalty(self):
        global loyalty, loyalty_names, user_name
        all_loyalty = pd.read_csv("loyalty.csv")
        loyalty = all_loyalty[all_loyalty['username'] == user_name]
        loyalty_names = list(loyalty['Name'])
        try:
            for i in range(len(loyalty_names)):
                self.loyalty_layout.children[i].disabled = False
        except:
            pass

    def save_barcode(self, name, code):
        barcode = EAN13(code, writer=ImageWriter())
        barcode.save(name)

    def load_loyalty(self):
        global loyalty, loyalty_names
        self.read_loyalty()
        for name in loyalty_names:
            button = MDRaisedButton(id=name, text=name)
            button.bind(on_release=lambda btn=name: self.button_press(btn))
            button.disabled = False
            self.loyalty_layout.add_widget(button)
        self.add_widget(self.loyalty_layout)

    def unload_loyalty(self):
        global loyalty_names

        try:
            for i in range(len(loyalty_names)):
                self.loyalty_layout.remove_widget(self.loyalty_layout.children[i])
        except:
            pass
        self.remove_widget(self.loyalty_layout)

    def button_press(self, btn):
        global loyalty_code, loyalty
        self.manager.current = 'scan'
        self.manager.ids.scanscreen.ids.loyaltyname.text = btn.text + ' card'
        loyalty_code = str(int(loyalty[loyalty["Name"] == btn.text]["Code"].values[0]))
        self.save_barcode(btn.text, loyalty_code)
        self.manager.ids.scanscreen.ids.loyaltybarcode.source = btn.text+'.png'
        self.clear_loyalty()
        btn.disabled = True
        return btn.text


class ScanScreen(MDScreen):
    def scan_loyalty(self):
        self.manager.ids.homescreen.ids.loyalty.disabled = True
        time.sleep(SCAN_TIME)
        self.manager.current = 'home'


class ShowScreen(MDScreen):
    def load_table(self):
        global trans
        self.cols = trans.columns.values
        self.values = trans.values.tolist()
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

    def close_table(self, obj):
        self.manager.current = 'home'


class ShowPotsScreen(MDScreen):
    def load_table(self):
        global pots
        self.cols = pots.columns.values
        self.values = pots.values.tolist()

        layout = MDBoxLayout(orientation='vertical', spacing=0.01 * self.height)
        column_data = [(col, dp(15)) for col in self.cols]
        row_data = self.values
        self.table = MDDataTable(column_data=column_data, row_data=row_data,
                                 rows_num=100, size_hint=(0.9, 0.5), pos_hint={'center_x': 0.5, 'center_y': 0.7})
        self.button1 = MDFlatButton(text="Add a new pot", on_press=self.create_pot,
                                    pos_hint={'center_x': 0.2})
        self.button2 = MDFlatButton(text="Home", on_press=self.close_table,
                                    pos_hint={'center_x': 0.8})
        self.add_widget(self.table)
        self.add_widget(self.button1)
        self.add_widget(self.button2)
        self.pie_chart = FigureCanvasKivyAgg(self.create_pie_chart())
        self.pie_chart.print_png('pie_chart.png')
        self.pie_image = Image(source='pie_chart.png', pos_hint={'center_y': 0.3}, size_hint=(0.9, 0.5))
        self.add_widget(self.pie_image)
        return layout

    def create_pie_chart(self):
        global pots, pot_names
        values = pots['Limit'].tolist()
        fig, ax = plt.subplots()
        ax.pie(values, labels=pot_names, autopct='%1.1f%%')
        return fig

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

    #sort_layout = MDBoxLayout(orientation='vertical')

    def get_transactions(self):
        global trans, user_name
        all_trans = pd.read_csv('transactions.csv')
        trans = all_trans[all_trans['username'] == user_name]
        self.unsorted_rows = trans[trans["pot"] == "None"]
        self.unsorted_rows = self.unsorted_rows[['id', 'amount', 'pot']]
        #self.unsorted_rows['date'] = self.unsorted_rows['timestamp'].str[:10]
        #self.unsorted_rows.drop('timestamp', axis=1, inplace=True)
        self.cols = self.unsorted_rows.columns.values
        self.num_cols = len(self.cols)
        self.values = trans.values.tolist()
        self.unsorted_values = self.unsorted_rows.values.tolist()

    def load_table(self):
        self.get_transactions()
        layout = MDBoxLayout(orientation='vertical', spacing=0.01*self.height)
        column_data = [(col, dp(10)) for col in self.cols]
        row_data = self.unsorted_values
        self.unsorted_table = MDDataTable(column_data=column_data, row_data=row_data, rows_num=100)
                                          #size_hint=(1.0, 0.9), pos_hint={'center_x': 0.5, 'center_y': 0.55})
        self.unsorted_table.bind(on_row_press=self.on_row_press)
        self.unsorted_table.bind(on_check_press=self.on_check_press)
        self.add_widget(self.unsorted_table)
        self.button = MDFlatButton(text="Home", on_press=self.close_table)
        #self.sort_layout.add_widget(self.button)
        self.add_widget(self.button)



    def show_table(self):
        self.load_table()

    def close_table(self, obj):
        self.manager.current = 'home'

    def on_row_press(self, instance_table, instance_row):
        global pots
        self.selected_row_id = instance_row.table.row_data[instance_row.index//self.num_cols][0]
        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)
        buttons = []
        for pot in list(pots['Name']):
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

    def assign_pot(self, btn):
        global unsorted, trans, pots, user_name
        trans.loc[trans['id'] == self.selected_row_id, 'pot'] = btn.text
        sort_amount = trans.loc[trans['id'] == self.selected_row_id, 'amount'].values[0]
        all_trans = pd.read_csv('transactions.csv')
        other_trans = all_trans[all_trans['username'] != user_name]
        all_trans = trans.append(other_trans)
        all_trans.to_csv('transactions.csv', index=False)
        self.get_transactions()
        pot_limit = pots[pots["Name"] == btn.text]["Limit"].values[0]
        pots.loc[pots['Name'] == btn.text, 'Balance'] -= float(sort_amount)
        pots.loc[pots['Name'] == btn.text, 'Weight'] += 1
        pot_balance = pots[pots["Name"] == btn.text]["Balance"].values[0]
        pots.loc[pots['Name'] == btn.text, 'Usage'] = '{:.0%}'.format(
            round((float(pot_limit) - float(pot_balance)) / float(pot_limit), 2))
        self.manager.ids.homescreen.update_pot_buttons()
        self.show_table()
        unsorted = trans[trans["pot"] == "None"].shape[0]
        self.manager.ids.homescreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.loyaltyscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.justpayscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.potpayscreen.ids.sort.text = f"Sort({unsorted})"
        self.manager.ids.potpaidscreen.ids.sort.text = f"Sort({unsorted})"
        self.dialog.dismiss()

    def close_dialog(self, obj):
        self.dialog.dismiss()

    def on_check_press(self, instance_table, current_row):
        print(current_row)


class NewPotScreen(MDScreen):

    def load_new_pot(self, newpot):
        global pots, pot_names, user_name
        all_pots = pd.read_csv("pots.csv")
        pots = all_pots[all_pots['username'] == user_name]
        pot_names = list(pots['Name'])

        if newpot in pot_names:
            button = MDRaisedButton(id=newpot, text=f'{newpot}-0% (0)')
            button.bind(on_release=lambda btn=newpot: self.manager.ids.homescreen.button_press(btn))
            button.disabled = False
            self.manager.ids.homescreen.pot_layout.add_widget(button)

    def add_pot(self, pot_name, pot_limit):
        global pots, pot_names
        if pot_limit == '':
            check_string = f'Pot limit is empty!'
        else:
            try:
                data_entry = [pot_name, pot_limit, pot_limit, "0%", 0, user_name]
                with open('pots.csv', 'a', newline='') as file:
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
        global pots, pot_names, user_name
        all_pots = pd.read_csv('pots.csv')
        pots = all_pots[all_pots['username'] == user_name]
        pot_names = list(pots['Name'])
        self.dialog.dismiss()
        self.manager.ids.showpotsscreen.show_table()


class NewLoyaltyScreen(MDScreen):
    loyalty_layout = StackLayout()

    def load_new_loyalty(self, new):
        global loyalty, loyalty_names, user_name
        all_loyalty = pd.read_csv("loyalty.csv")
        loyalty = all_loyalty[all_loyalty['username'] == user_name]
        loyalty_names = list(loyalty['Name'])

        if new in loyalty_names:
            button = MDRaisedButton(id=new, text=new)
            button.bind(on_release=lambda btn=new: self.manager.ids.loyaltyscreen.button_press(btn))
            button.disabled = False
            self.manager.ids.loyaltyscreen.loyalty_layout.add_widget(button)

    def add_loyalty(self, loyalty_name, loyalty_code):
        if len(loyalty_code) != 12:
            check_string = "Invalid loyalty code!"
        else:
            try:
                data_entry = [loyalty_name, loyalty_code, user_name]
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
        global loyalty, loyalty_names, user_name
        all_loyalty = pd.read_csv("loyalty.csv")
        loyalty = all_loyalty[all_loyalty['username'] == user_name]
        loyalty_names = list(loyalty['Name'])
        self.dialog.dismiss()
        self.manager.current = 'loyalty'


class DemoApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Cyan"
        self.theme_cls.primary_hue = "900"
        self.theme_cls.theme_style = "Light"
        kv = Builder.load_file("helper.kv")
        return kv


if __name__ == "__main__":
    DemoApp().run()

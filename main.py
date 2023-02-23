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
import string
from barcode import EAN13
from barcode.writer import ImageWriter
from uuid import uuid4


Window.size = (300, 500)  # for mobile phones only


# Set up your PayPal API credentials
client_id = "AfODQAuk-f-Ait4OKTHweC-hBhqIQXVkDaDDOgnrn8uNG9pS_tO9kfG71mevAyvIRKiLsD5d5KyMoZ09"
client_secret = "EO0NHZ2yztKGLMcvEFLZw7dapQHHk6CKDfA2gYGw6aGK3rYNc7IbzgINrn8xbPEIcGJtl-ux7UXBvjLI"


class WindowManager(MDScreenManager):
    pass


class HomeScreen(MDScreen):

    pay_amount = str(round(random.uniform(0.00, 9.99), 2))

    def read_pots(self):
        self.pots = pd.read_csv("pots.csv")
        self.pot_names = list(self.pots['Name'])
        self.pot_limits = list(self.pots['Limit'])
        self.pot_rems = list(self.pots["Balance"])

    pot_selected = "None"

    pot_layout = StackLayout()

    def get_amount(self):
        new_amount = str(round(random.uniform(0.00, 9.99), 2))
        self.pay_amount = new_amount
        self.ids.amount.text = "Amount: " + self.pay_amount + " GBP"
        self.ids.value.text = self.pay_amount
        self.manager.ids.payscreen.ids.value.text = self.pay_amount
        self.manager.ids.payscreen.ids.paynow.disabled = False
        self.manager.ids.potscreen.ids.confirm.disabled = False
        self.manager.ids.payscreen.ids.potname.text = "None"
        self.manager.ids.potscreen.ids.potname.text = "None"
        self.ids.justpay.disabled = False
        self.ids.loyalty.disabled = False
        self.clear_pots()

    def load_pots(self):
        self.read_pots()
        for name in self.pot_names:
            button = MDRaisedButton(id=name, text=name)
            button.bind(on_release=lambda btn=name: self.button_press(btn))
            button.disabled = False
            self.pot_layout.add_widget(button)
        self.add_widget(self.pot_layout)

    def load_new_pot(self, newpot):
        button = MDRaisedButton(id=newpot, text=newpot)
        button.bind(on_release=lambda btn=newpot: self.button_press(btn))
        button.disabled = False
        self.pot_layout.add_widget(button)

    def button_press(self, btn):
        self.read_pots()
        self.pot_selected = btn.text
        self.manager.current = 'pot'
        self.manager.ids.potscreen.ids.amount.text = "Amount: " + self.pay_amount + " GBP"
        self.manager.ids.potscreen.ids.value.text = self.pay_amount
        self.manager.ids.payscreen.ids.amount.text = "Amount: " + self.pay_amount + " GBP"
        self.manager.ids.payscreen.ids.value.text = self.pay_amount
        self.manager.ids.potscreen.ids.potname.text = btn.text
        self.manager.ids.payscreen.ids.potname.text = btn.text
        pot_limit = str(self.pots[self.pots["Name"] == btn.text]["Limit"].values[0])
        self.manager.ids.potscreen.ids.potlimit.text = "Limit\n"+pot_limit
        pot_balance = str(self.pots[self.pots["Name"] == btn.text]["Balance"].values[0])
        self.manager.ids.potscreen.ids.potrem.text = "Balance\n" + pot_balance
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


class PayScreen(MDScreen):
    amount = "0.00"
    pot = "None"

    home = HomeScreen()
    amount = home.pay_amount
    pot = home.pot_selected

    pots = pd.read_csv("pots.csv")

    def read_transactions(self):
        self.transactions = pd.read_csv("transactions.csv")
        self.cols = self.transactions.columns.values
        self.values = self.transactions.values.tolist()

    def just_pay(self, btn, amount, loyalty):
        self.pay_amount(amount, loyalty)
        btn.disabled = True
        self.manager.current = 'home'
        self.manager.ids.homescreen.ids.justpay.disabled = True
        self.manager.ids.homescreen.ids.loyalty.disabled = True
        self.manager.ids.potscreen.ids.confirm.disabled = True
        self.manager.ids.homescreen.disable_pots()

    def pay_amount(self, amount, loyalty):
        letters = string.ascii_lowercase
        batch_code = "".join(random.choice(letters) for i in range(200))
        #batch_code = '123'
        access_token, response_text = \
            make_payment(client_id, client_secret, amount, batch_code)

        now = datetime.now()
        dt_string = now.strftime("%Y%m%d %H:%M:%S")
        id = dt_string[:8] + dt_string[9:11] + dt_string[12:14]+dt_string[-2:]
        try:
            data_entry = [id, amount, "None", loyalty, dt_string]
            with open('transactions.csv', 'a', newline='') as file:
                writer_object = writer(file)
                writer_object.writerow(data_entry)
                file.close()
            check_string = "Transaction added successfully."
        except:
            check_string = "Failed to update the transaction."

        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)

        self.dialog = MDDialog(title="Payment status",
                               text=response_text+"\n"+check_string + "\n Spent " + amount +
                                    " GBP\n without choosing a pot",
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def load_table(self):
        self.read_transactions()
        layout = MDBoxLayout(orientation='vertical', spacing=0.01*self.height)
        column_data = [(col, dp(30)) for col in self.cols]
        row_data = self.values
        self.table = MDDataTable(column_data=column_data, row_data=row_data, rows_num=100)
        self.button = MDFlatButton(text="Home", on_press=self.close_table)
        self.add_widget(self.table)
        self.add_widget(self.button)
        return layout

    def show_table(self):
        self.load_table()

    def close_table(self, obj):
        self.manager.current = 'home'

    def close_dialog(self, obj):
        self.dialog.dismiss()


class PotScreen(MDScreen):
    home = HomeScreen()
    amount = home.pay_amount

    def confirm_pay(self, btn, pot, amount, loyalty):
        self.manager.current = 'home'
        self.pay_amount(pot, amount, loyalty)
        btn.disabled = True
        self.manager.ids.homescreen.ids.justpay.disabled = True
        self.manager.ids.homescreen.ids.loyalty.disabled = True
        self.manager.ids.payscreen.ids.paynow.disabled = True
        self.manager.ids.homescreen.disable_pots()

    def pay_amount(self, pot, amount, loyalty):
        letters = string.ascii_lowercase
        batch_code = "".join(random.choice(letters) for i in range(200))
        access_token, response_text = \
            make_payment(client_id, client_secret, amount, batch_code)

        now = datetime.now()
        dt_string = now.strftime("%Y%m%d %H:%M:%S")
        id = dt_string[:8] + dt_string[9:11] + dt_string[12:14]+dt_string[-2:] #+ str(uuid4())
        try:
            data_entry = [id, amount, pot, loyalty, dt_string]
            with open('transactions.csv', 'a', newline='') as file:
                writer_object = writer(file)
                writer_object.writerow(data_entry)
                file.close()
            check_string = "Transaction added successfully."
        except:
            check_string = "Failed to update the transaction."

        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)

        self.dialog = MDDialog(title="Payment status",
                               text=response_text+"\n"+check_string + "\n Spent " + amount + " GBP\n from "
                                    + pot + "Pot.",
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def close_dialog(self, obj):
        self.dialog.dismiss()


class PotPayScreen(MDScreen):
    home = HomeScreen()
    pot_selected = home.pot_selected


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

    def load_new_loyalty(self, new):
        self.read_loyalty()
        button = MDRaisedButton(id=new, text=new)
        button.bind(on_release=lambda btn=new: self.button_press(btn))
        button.disabled = False
        self.loyalty_layout.add_widget(button)

    def button_press(self, btn):
        self.read_loyalty()
        self.manager.current = 'preloyalty'
        self.manager.ids.loyaltyprescreen.ids.loyaltyname.text = btn.text + ' card'
        self.manager.ids.loyaltyprescreen.ids.loyalty.text = btn.text
        loyalty_code = str(int(self.loyalty[self.loyalty["Name"] == btn.text]["Code"].values[0]))
        self.save_barcode(btn.text, loyalty_code)
        self.manager.ids.loyaltyprescreen.ids.loyaltycode.text = loyalty_code
        self.manager.ids.loyaltyprescreen.ids.loyaltybarcode.source = btn.text+'.png'
        self.clear_loyalty()
        btn.disabled = True
        return btn.text


class LoyaltyPreScreen(MDScreen):

    def read_loyalty(self):
        self.loyalty = pd.read_csv("loyalty.csv")
        self.loyalty_names = list(self.loyalty['Name'])
        self.loyalty_codes = list(self.loyalty['Code'])

    def scan_loyalty(self, card):
        self.read_loyalty()
        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)
        loyalty_code = str(int(self.loyalty[self.loyalty["Name"] == self.ids.loyalty.text]["Code"].values[0]))
        self.manager.ids.loyaltypostscreen.ids.loyaltycode.text = loyalty_code
        self.dialog = MDDialog(title="Loyalty scan",
                               text=card + " scanned successfully",
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def close_dialog(self, obj):
        self.dialog.dismiss()


class LoyaltyPostScreen(MDScreen):
    pass


class ShowScreen(MDScreen):
    pass


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
        column_data = [(col, dp(30)) for col in self.cols]
        row_data = self.unsorted_values
        self.unsorted_table = MDDataTable(column_data=column_data, row_data=row_data, rows_num=100, check=True)
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
        self.transactions.loc[self.transactions['timestamp'] == self.selected_row_id, 'pot'] = instance.text
        self.transactions.to_csv('transactions.csv', index=False)
        self.get_transactions()

    def close_dialog(self, obj):
        self.dialog.dismiss()
        self.show_table()

    def on_check_press(self, instance_table, current_row):
        print(current_row)

    def dropdown(self, instance):
        self.menu_list = [
            {
                "viewclass": "OneLineListItem",
                "text": "Grocery",
                "on_release": lambda x="Grocery": self.pot1()
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Fuel",
                "on_release": lambda x="Grocery": self.pot2()
            }

        ]
        self.menu = MDDropdownMenu(items=self.menu_list, width_mult=4)
        self.menu.caller = instance
        self.menu.open()

    def pot1(self):
        print("Pot 1 is pressed.")

    def pot2(self):
        print("Pot 2 is pressed.")


class NewPotScreen(MDScreen):

    pots = pd.read_csv("pots.csv")
    pot_names = list(pots['Name'])
    pot_limits = list(pots['Limit'])
    pot_rems = list(pots["Balance"])

    name_layout = StackLayout()
    limit_layout = StackLayout()
    rem_layout = StackLayout()

    def load_names(self):
        for name in self.pot_names:
            label = MDLabel(id=name, text=name)
            self.name_layout.add_widget(label)
        self.add_widget(self.name_layout)

    def load_limits(self):
        for i, limit in enumerate(self.pot_limits):
            label = MDLabel(id="limit"+str(i+1), text=str(limit))
            self.limit_layout.add_widget(label)
        self.add_widget(self.limit_layout)

    def load_rems(self):
        for i, rem in enumerate(self.pot_rems):
            label = MDLabel(id="rem"+str(i+1), text=str(rem))
            self.rem_layout.add_widget(label)
        self.add_widget(self.rem_layout)

    def add_pot(self, pot_name, pot_limit):
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

    def add_loyalty(self, loyalty_name, loyalty_code):
        if len(loyalty_code) != 12:
            check_string = "Invalid loyalty code!"
        else:
            try:
                data_entry = [loyalty_name, loyalty_code]
                with open('loyalty.csv', 'a') as file:
                    writer_object = writer(file)
                    writer_object.writerow(data_entry)
                    file.close()
                check_string = f"{loyalty_name} loyalty card added successfully"
            except:
                check_string = "Failed to add the loyalty card"

        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)

        self.dialog = MDDialog(title="Adding a new loyalty card",
                               text= check_string,
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def close_dialog(self, obj):
        self.dialog.dismiss()


class DemoApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Cyan"
        self.theme_cls.primary_hue = "900"
        self.theme_cls.theme_style = "Light"
        kv = Builder.load_file("helper.kv")
        return kv



if __name__ == "__main__":
    DemoApp().run()

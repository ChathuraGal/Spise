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


Window.size = (300, 500)  # for mobile phones only


# Set up your PayPal API credentials
client_id = "AfODQAuk-f-Ait4OKTHweC-hBhqIQXVkDaDDOgnrn8uNG9pS_tO9kfG71mevAyvIRKiLsD5d5KyMoZ09"
client_secret = "EO0NHZ2yztKGLMcvEFLZw7dapQHHk6CKDfA2gYGw6aGK3rYNc7IbzgINrn8xbPEIcGJtl-ux7UXBvjLI"
transactions = pd.read_csv("transactions.csv")


class WindowManager(MDScreenManager):
    pass


class HomeScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    pay_amount = str(round(random.uniform(0.00, 99.99), 2))

    pots = pd.read_csv("pots.csv")
    pot_names = list(pots['Name'])
    pot_limits = list(pots['Limit'])
    pot_rems = list(pots["Balance"])

    pot_selected = ""

    pot_layout = StackLayout()

    def get_transaction(self):
        new_amount = str(round(random.uniform(0.00, 99.99), 2))
        return new_amount

    def load_pots(self):
        for name in self.pot_names:
            button = MDRaisedButton(id=name, text=name)
            button.bind(on_release=lambda btn=name: self.button_press(btn))
            button.disabled = False
            self.pot_layout.add_widget(button)
        self.add_widget(self.pot_layout)

    def button_press(self, btn):
        self.pot_selected = btn.text
        self.manager.current = 'pot'
        self.manager.ids.potscreen.ids.potname.text = "Pot\n" + btn.text
        pot_limit = str(self.pots[self.pots["Name"] == btn.text]["Limit"].values[0])
        self.manager.ids.potscreen.ids.potlimit.text = "Limit\n"+pot_limit
        pot_balance = str(self.pots[self.pots["Name"] == btn.text]["Balance"].values[0])
        self.manager.ids.potscreen.ids.potrem.text = "Balance\n" + pot_balance
        self.clear_pots()
        btn.disabled = True
        return btn.text

    def clear_pots(self):
        try:
            for i in range(len(self.pot_names)):
                self.pot_layout.children[i].disabled = False
        except:
            pass


class PayScreen(MDScreen):
    home = HomeScreen()
    amount = home.pay_amount
    pot = home.pot_selected

    pots = pd.read_csv("pots.csv")
    cols = transactions.columns.values
    values = transactions.values.tolist()

    def pay_amount(self):
        letters = string.ascii_lowercase
        batch_code = "".join(random.choice(letters) for i in range(200))
        #batch_code = '123'
        access_token, response_text = \
            make_payment(client_id, client_secret, self.amount, batch_code)

        now = datetime.now()
        dt_string = now.strftime("%Y%m%d %H:%M:%S")
        try:
            data_entry = [self.amount, self.pot, dt_string]
            with open('transactions.csv', 'a') as file:
                writer_object = writer(file)
                writer_object.writerow(data_entry)
                file.close()
            check_string = "transaction added successfully"
        except:
            check_string = "Failed to update the transaction"

        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)

        self.dialog = MDDialog(title="Payment status",
                               text=response_text+"\n"+check_string + "\n" + self.amount + "\n" + self.pot ,
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def load_table(self):
        layout = MDBoxLayout(orientation='vertical', spacing=0.01*self.height)
        column_data = [(col, dp(30)) for col in self.cols]
        row_data = self.values
        self.table = MDDataTable(column_data=column_data, row_data=row_data, rows_num=100, check=True)
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
    pot_selected = home.pot_selected


class PotPayScreen(MDScreen):
    home = HomeScreen()
    pot_selected = home.pot_selected


class LoyaltyScreen(MDScreen):
    loyalty = pd.read_csv("loyalty.csv")
    loyalty_names = list(loyalty['Name'])
    loyalty_codes = list(loyalty['Code'])

    loyalty_layout = StackLayout()

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
        for name in self.loyalty_names:
            button = MDRaisedButton(id=name, text=name)
            button.bind(on_release=lambda btn=name: self.button_press(btn))
            button.disabled = False
            self.loyalty_layout.add_widget(button)
        self.add_widget(self.loyalty_layout)

    def button_press(self, btn):
        self.manager.current = 'preloyalty'
        self.manager.ids.loyaltyprescreen.ids.loyaltyname.text = btn.text + ' card'
        loyalty_code = str(int(self.loyalty[self.loyalty["Name"] == btn.text]["Code"].values[0]))
        self.save_barcode(btn.text, loyalty_code)
        #self.manager.ids.loyaltyprescreen.ids.loyaltycode.text = loyalty_code
        self.manager.ids.loyaltyprescreen.ids.loyaltybarcode.source = btn.text+'.png'
        self.clear_loyalty()
        btn.disabled = True
        return btn.text

    def add_loyalty(self, loyalty_name, loyalty_code):
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
        proceed_button = MDFlatButton(text="Close", on_release=self.proceed_dialog)

        self.dialog = MDDialog(title="Adding a new loyalty card",
                               text= check_string,
                               size_hint=(0.7, 1), buttons=[close_button])
        self.dialog.open()

    def close_dialog(self, obj):
        self.dialog.dismiss()

    def proceed_dialog(self, obj):
        self.manager.current = 'home'


class SortScreen(MDScreen):
    home = HomeScreen()
    pot_names = home.pot_names

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
                               text=check_string,
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

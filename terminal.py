import datetime
import random
import socket
import string
from datetime import datetime
import time
import threading
from _csv import writer

from kivy.clock import Clock
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from pandas.core.window import Window

from paypal import make_payment


Window.size = (300, 500)  # for mobile phones only

send_cond = False
recv_cond = False

paid_amount = 0.00
client_data = ''

PHONE_IP = socket.gethostbyname(socket.gethostname())
PORT_NUMBER = 5005
SIZE = 1024


def sender():
    global paid_amount, send_cond
    while True:
        try:
            while send_cond:
                send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                send_socket.connect((PHONE_IP, PORT_NUMBER))
                print('connect')
                while True:
                    if paid_amount != '':
                        send_socket.send(bytes(paid_amount, 'utf-8'))
                        paid_amount = ''
        except:
            time.sleep(0.5)


thread_1 = threading.Thread(target=sender)


def receiver():
    global client_data, recv_cond

    while recv_cond:
        try:
            recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            recv_socket.bind((PHONE_IP, PORT_NUMBER))
            recv_socket.listen(10)
            print('binded')
            while True:
                listen_socket, address = recv_socket.accept()
                while True:
                    raw_msg = listen_socket.recv(1024)
                    client_data = raw_msg.decode('utf-8')
        except:
            time.sleep(0.5)
            print('binding...')


thread_2 = threading.Thread(target=receiver)


class WindowManager(MDScreenManager):
    pass


class WelcomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def initiate(self):
        global send_cond
        send_cond = True
        self.manager.current = 'mainscreen'
        Clock.schedule_interval(self.manager.ids.mainscreen.listen, 0.5)


class MainScreen(MDScreen):
    client_details = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    pay_amount = str(round(random.uniform(0.00, 9.99), 2))
    paid_amount = 0.00

    def listen(self, *args):
        global client_data
        if client_data != '':
            print(client_data)
            client_data = ''

    def send(self):
        global paid_amount
        paid_amount = self.pay_amount

    def handle(self, conn, addr):
        while True:
            data = conn.recv(SIZE)
            if not data:
                break
            print(f"Received message from {addr[0]}: {data.decode()}")
            self.ids.label.text = data.decode()
        conn.close()

    def get_amount(self):
        new_amount = "%.2f" % round(random.uniform(0.00, 9.99), 2)  # keeps 2 decimal points with trailing zeros
        self.pay_amount = new_amount
        self.ids.amount.text = "Amount: " + self.pay_amount + " GBP"
        self.ids.value.text = self.pay_amount

    def get_client_data(self):
        global client_data
        # Set up your PayPal API credentials
        client_id = "AfODQAuk-f-Ait4OKTHweC-hBhqIQXVkDaDDOgnrn8uNG9pS_tO9kfG71mevAyvIRKiLsD5d5KyMoZ09"
        client_secret = "EO0NHZ2yztKGLMcvEFLZw7dapQHHk6CKDfA2gYGw6aGK3rYNc7IbzgINrn8xbPEIcGJtl-ux7UXBvjLI"
        client_data = client_id+client_secret
        self.client_details = client_data

    def pay(self):
        global client_data
        client_id = client_data[:80]
        client_secret = client_data[80:]

        client_id = self.client_details[:80]
        client_secret = self.client_details[80:]

        letters = string.ascii_lowercase
        batch_code = "".join(random.choice(letters) for i in range(200))
        #batch_code = '123' #inorder to make the payment fail
        response = make_payment(client_id, client_secret, self.pay_amount, batch_code)

        # Check the response to see if the payment was successful
        if response.status_code == 201:
            response_text = "Payment sent successfully!"
            now = datetime.now()
            dt_string = now.strftime("%Y%m%d %H:%M:%S")
            id = str(int(dt_string[:8] + dt_string[9:11] + dt_string[12:14] + dt_string[-2:]))
            try:
                data_entry = [id, self.pay_amount, dt_string]
                with open('terminal_transactions.csv', 'a', newline='') as file:
                    writer_object = writer(file)
                    writer_object.writerow(data_entry)
                    file.close()
                    check_string = f"Transaction of {self.pay_amount} GBP added successfully."
            except:
                check_string = "Failed to update the transaction."


        else:
            response_text = f"Payment failed: {response.status_code}"
            check_string = ''



        close_button = MDFlatButton(text="Close", on_release=self.close_dialog)
        send_button = MDFlatButton(text='Send', on_press=self.send)

        self.dialog = MDDialog(title="Payment status",
                               text=response_text+"\n"+check_string,
                               size_hint=(0.7, 1), buttons=[close_button, send_button])
        self.dialog.open()

    def close_dialog(self):
        self.dialog.dismiss()


class TerminalApp(MDApp):
    def build(self):
        return Builder.load_file('terminal.kv')


if __name__ == "__main__":
    thread_1.start()
    thread_2.start()
    threading.Thread(target=TerminalApp().run())
    send_cond = False
    recv_cond = False

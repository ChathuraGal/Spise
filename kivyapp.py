from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen


class MainWindow(MDScreen):
    pass


class SecondWindow(MDScreen):
    pass


class WindowManager(MDScreenManager):
    pass


kv = Builder.load_file("my.kv")


class MyApp(MDApp):
    def build(self):
        self.root = Builder.load_file("my.kv")


if __name__ =="__main__":
    MyApp().run()
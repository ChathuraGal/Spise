from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.lang import Builder


class ScrollableStackLayout(BoxLayout):
    pass


class MyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scrollable_stack_layout = ScrollableStackLayout()
        self.add_widget(self.scrollable_stack_layout)

    def on_enter(self, *args):
        # Create buttons dynamically and add them to the stack layout
        stack_layout = self.scrollable_stack_layout.ids.stack_layout
        button_height = 50  # height of each button
        total_height = button_height * 100  # total height of all buttons
        for i in range(100):
            button = Button(text=f"Button {i}", size_hint=(1, None), height=button_height)
            stack_layout.add_widget(button)
        # Set the height of the ScrollView to be the height of the StackLayout
        self.scrollable_stack_layout.ids.scroll_view.height = total_height


kv = '''
<ScrollableStackLayout>:
    ScrollView:
        StackLayout:
            id: stack_layout

<MyScreen>:
'''


class MyApp(App):
    def build(self):
        screen_manager = ScreenManager()
        screen_manager.add_widget(MyScreen(name='my_screen'))
        return screen_manager


if __name__ == '__main__':
    Builder.load_string(kv)
    MyApp().run()

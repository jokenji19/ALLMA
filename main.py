
import os
import kivy
from kivy.app import App
from kivy.uix.label import Label

class AllmaPrimeApp(App):
    def build(self):
        return Label(text="ALLMA PRIME: Build 129 SUCCESS\n(Sanity Check Passed)", halign="center")

if __name__ == "__main__":
    AllmaPrimeApp().run()

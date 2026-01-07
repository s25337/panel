
import PySimpleGUI as sg
print("Loaded from:", getattr(sg, "__file__", None))
print("Version:", getattr(sg, "__version__", "unknown"))
print("Has Text?", hasattr(sg, "Text"))

layout = [[sg.Text("Hello")],[sg.Button("OK")]]
sg.Window("PSG test", layout).read(close=True)


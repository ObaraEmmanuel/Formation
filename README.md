![Formation logo](https://raw.githubusercontent.com/obaraemmanuel/Formation/master/docs/_static/logo.png)

![license](https://img.shields.io/github/license/ObaraEmmanuel/Formation)
![tests](https://github.com/ObaraEmmanuel/Formation/workflows/build/badge.svg)
[![pypi version](https://img.shields.io/pypi/v/formation-studio.svg)](https://pypi.org/project/formation-studio/)
![python version](https://img.shields.io/badge/python-3.6+-blue.svg)
![platforms](https://img.shields.io/badge/Platforms-Linux%20|%20Windows%20|%20Mac%20(partial)-purple.svg)
[![Documentation Status](https://readthedocs.org/projects/formation-studio/badge/?version=latest)](https://formation-studio.readthedocs.io/en/latest/?badge=latest)
## Introduction

**Formation studio** is a tool that makes developing User interfaces in python a breeze. It allows developers to focus
on product functionality by doing the heavy lifting in terms of writing the interface code. Using a set of powerful
tools, developers can quickly design interfaces, save them as
[XML](https://en.wikipedia.org/wiki/XML) files and load them into their code. Formation studio draws inspiration from
other
[RAD](https://en.wikipedia.org/wiki/Rapid_application_development) tools such as
[Android Studio's](https://developer.android.com/studio) visual layout editor,
[PAGE](http://page.sourceforge.net). The XML format used is largely similar to one used by android layout files. It
currently supports both tkinter and it's ttk extension. Other file formats other than XML are now supported for instance
JSON.

## Getting started

### Installation

To use formation studio you will need to have installed python version 3.6 or higher. You can download and install
python from [here](https://www.python.org/downloads/)
.Proceed then and install formation using pip. This will install the latest stable version.

```bash
pip install formation-studio
```

If you want to install the development version directly from the master branch, the following command should suffice.
> **note**: You will need to have installed git on your system as well as the stable formation studio release as shown above

```bash
pip install --upgrade git+https://github.com/obaraemmanuel/Formation@master
```

### Installation on Linux

Formation studio uses tkinter and depending on the distro you are using it may or may not
be installed by default. If you are using tkinter for the first time on your machine you
might want to first install `tkinter` and `imagetk` after completing the installation procedure above. 
For debian based distros it should be something like

```bash
sudo apt-get install python3-tk, python3-pil.imagetk
```

> Note: These are instructions for Debian based distros and is only assured to work on Ubuntu. For
> other distros, sub the installation command with the right one. Also, these commands install
> to ``python 3`` installations. Formation studio does not support python 2 so ensure you install 
> python 3 packages only.

### Launching

After a successful installation, you can launch the studio from the command line using the command

```bash
formation-studio
```

The studio will open with a blank design (This can be modified in the preferences). Below is a sample of the studio in
action. With detachable tool windows, the studio is able to provide the flexibility required to get things done quickly.

![Formation window](https://raw.githubusercontent.com/obaraemmanuel/Formation/master/docs/_static/showcase.png)

You can select widgets from the _**Components**_ pane at the top and drag them onto the stage. Click to select widgets
on the workspace and customize them on _**Stylepane**_ to the right. You can view your widget hierarchies from the _**
Component tree**_ at the bottom left. To preview the the design, use the preview ("run button") on the toolbar. After
you are satisfied with the design, save by heading to the menubar _File > Save_. Below is a sample studio preview saved
as `hello.xml`

<p align="center">
    <img alt="sample design" src="https://raw.githubusercontent.com/obaraemmanuel/Formation/master/docs/_static/hello.png"/>
</p>

The underlying xml uses namespaces and is as shown below:

```xml
<tkinter.Frame 
    xmlns:attr="http://www.hoversetformationstudio.com/styles/" 
    xmlns:layout="http://www.hoversetformationstudio.com/layouts/" 
    name="Frame_1" 
    attr:layout="place" 
    layout:width="616" 
    layout:height="287" 
    layout:x="33" 
    layout:y="33">
    <tkinter.ttk.Label 
        name="myLabel" 
        attr:foreground="#44c33c" 
        attr:font="{Calibri} 20 {}" 
        attr:anchor="center" attr:text="Hello World!" 
        layout:width="539" 
        layout:height="89" 
        layout:x="41" 
        layout:y="41"/>
    <tkinter.ttk.Button 
        name="myButton"
        attr:command="on_click"
        attr:text="Click me" 
        layout:width="95" 
        layout:height="30" 
        layout:x="266" 
        layout:y="204"/>
</tkinter.Frame>

```

> Note: this xml file has been manually formatted to make it more legible. The actual xml file
> is minimally formatted since it's not expected that the developer will need to modify the xml
> file manually

To load the design in your python code is as simple as:

```python
# import the formation library which loads the design for you
from formation import AppBuilder

def on_click(event):
    print("Button clicked")

app = AppBuilder(path="hello.xml")

app.connect_callbacks(globals()) # clicking the button will trigger the on_click function

print(app.myLabel["text"]) # outputs text in the label 'Hello world!'
print(app.myButton["text"]) # outputs text in the button 'Click me'

app.mainloop()
```

>Note: Its advisable that you use widget names that are valid python identifiers to avoid 
>possible issues while use the dot syntax to access the widget from the builder object.
>Use the widgets exact name as specified in the design to avoid `AttributeError`

For more details checkout the [documentation](https://formation-studio.readthedocs.io/en/latest/)
For those wishing to contribute, see the [studio notes](https://formation-studio.readthedocs.io/en/latest/studio/architecture.html) for developers and contributors
Some good documentation for building python user interfaces
include:

- [TkDocs](http://www.tkdocs.com)
- [Graphical User Interfaces with Tk](http://docs.python.org/3.5/library/tk.html)
- [An Introduction to Tkinter](https://web.archive.org/web/20170518202115/http://effbot.org/tkinterbook/tkinter-index.htm)
- [Tcl/Tk 8.5 Manual](http://www.tcl.tk/man/tcl8.5/) 

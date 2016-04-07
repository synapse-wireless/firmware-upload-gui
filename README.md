[![](https://cloud.githubusercontent.com/assets/1317406/12406044/32cd9916-be0f-11e5-9b18-1547f284f878.png)](http://www.synapse-wireless.com/)

# SNAPconnect Example - wx Firmware Uploader


![](https://cloud.githubusercontent.com/assets/1317406/14359686/3ccffc6e-fcb8-11e5-81d2-0824b9eebe21.gif)

This example demonstrates how you can combine the wxPython library and SNAP Connect
to create graphical interfaces that can interact with networks of SNAP devices. 
It allows you to connect to a bridge node, set your encryption type, 
and perform an over the air firmware upgrade of another node.

## Installing wxPython

This is example is intended to be used with Python 2.6-2.7 and wxPython 3.0.0-3.0.1.
Older or newer versions of Python and wxPython may also work, but have not been tested.

Windows and OSX binaries for wxPython can be found at [www.wxpython.org/download.php](http://www.wxpython.org/download.php).
For Linux systems, you can use whatever package manager is included with your distribution or build from source.

See [www.wxpython.org](http://www.wxpython.org) for more information.

## Running This Example

This example application has no command-line parameters, and requires no configuration,
other than installing SNAPconnect as a dependency:

```bash
pip install --extra-index-url https://update.synapse-wireless.com/pypi snapconnect
```
    
Once you have installed SNAPconnect and wxPython, simply run:

```bash
python FirmwareUpgrader.py
```

Running this command will launch the GUI.  Tooltips are included on each input to give more
details on how they can be used and what they correspond to when using SNAPconnect as a Python
library. See comments in [FirmwareUpgrader.py](FirmwareUpgrader.py) for information on how the GUI is tied into SNAPconnect.

After filling out the required information, this script can be used to upgrade the firmware of a given node.

## License

Copyright © 2016 [Synapse Wireless](http://www.synapse-wireless.com/), licensed under the [Apache License v2.0](LICENSE.md).

<!-- meta-tags: vvv-gui, vvv-wx, vvv-snapconnect, vvv-python, vvv-example -->

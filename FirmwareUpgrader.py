# (c) Copyright 2014-2015 Synapse Wireless, Inc.
"""FirmwareUpgrader provides a simple GUI for performing over the air
firmware upgrades of SNAP nodes.

This is intended to be an example of the firmware upgrade feature of SNAP Connect
and an example of integrating with wxPython.
"""
import wx
import binascii
import logging

from wx.lib import filebrowsebutton
from snapconnect import snap

log = logging.getLogger("FirmwareUpgrader")

###############################################
# Map display values to SNAP Connect Constants
SERIAL_PORT_TYPES = {
    'SNAPSTICK100' : snap.SERIAL_TYPE_SNAPSTICK100,
    'SNAPSTICK200' : snap.SERIAL_TYPE_SNAPSTICK200,
    'RS232'        : snap.SERIAL_TYPE_RS232,
}
CRYPTO_TYPES = {
    'Basic' : snap.ENCRYPTION_TYPE_BASIC,
    'AES'   : snap.ENCRYPTION_TYPE_AES128,
    'None'  : snap.ENCRYPTION_TYPE_NONE,
}

########################
# GUI Application Code
class FirmwareUpgradeFrame(wx.Frame):
    """The frame is the core of the firmware upgrader application.

    This frame allows you to provide input for the bridge connection,
    the encryption being used, the address to be upgraded, and the
    SFI file to be used with the upgrade.

    The frame provides you with a button to start or cancel upgrades, and
    it also displays status information through colored text and a progress
    bar that shows how close the upgrade is to completion.
    """
    def __init__(self):
        """Construct a window with GUI elements for starting an upgrade"""
        wx.Frame.__init__(self, None, title="SNAP Connect - OTA Firmware Upgrader", size=(600, 450))

        self.upgrade_in_progress = False # Are we currently upgrading?
        self.poll_time = 20 # Time in ms to poll SNAP Connect
        self.init_snap()    # Start the SNAP Connect instance and add necessary hooks
        self.init_ui()      # Build the application GUI

    def init_snap(self):
        """Create a SNAP Connect instance and add hooks for firmware upgrades"""
        self.comm = snap.Snap(funcs={})
        self.comm.set_hook(snap.hooks.HOOK_OTA_UPGRADE_COMPLETE, self._upgrade_complete_hook)
        self.comm.set_hook(snap.hooks.HOOK_OTA_UPGRADE_STATUS, self._upgrade_status_hook)
        self.comm.set_hook(snap.hooks.HOOK_SERIAL_OPEN, self._serial_open_hook)

        # Start polling the SNAP Connect instance
        # While running this script, the ws application MainLoop() will drive the program
        # Here, we tie the polling of SNAP Connect into the application loop for the GUI
        # We could also choose to run the SNAP Connect loop() function inside of a separate thread
        self.poller = wx.Timer(self, wx.NewId())
        self.Bind(wx.EVT_TIMER, self.poll_snap)
        self.poller.Start(self.poll_time, wx.TIMER_CONTINUOUS)

    def init_ui(self):
        """Construct the GUI elements"""
        row = 0 # Keep track of current row being added - This makes it easier to move things around
        header_font = wx.Font(15, wx.DECORATIVE, wx.NORMAL, wx.BOLD) #Larger font applied to header items

        ####################################################
        # Create a panel to hold our GUI elements
        self.panel = wx.Panel(self)

        ####################################################
        # Create a sizer to layout the subwindow within the panel
        # The GridBagSizer allows us to add elements to certain rows and columns
        # The vgap and hgap specify the spacing in between columns and rows
        sizer = wx.GridBagSizer(vgap=4, hgap=4)

        ####################################################
        # Add GUI elements for selecting the bridge node


        header_text = wx.StaticText(self.panel, label="Bridge Configuration")
        header_text.SetFont(header_font)
        sizer.Add(header_text, pos=(row, 0), span=(1,4), flag=wx.LEFT|wx.TOP, border=10)

        row+=1
        bridge_type_label = wx.StaticText(self.panel, label="Bridge Type")
        sizer.Add(bridge_type_label, pos=(row, 0), flag=wx.LEFT, border=10)

        self.bridge_type = wx.ComboBox(self.panel, choices=SERIAL_PORT_TYPES.keys(), style=wx.CB_READONLY|wx.CB_DROPDOWN)
        self.bridge_type.SetToolTip(wx.ToolTip("This would normally be the 1st argument passed to open_serial"))
        self.bridge_type.SetValue("RS232") #Set a default value
        sizer.Add(self.bridge_type, pos=(row, 1), span=(1, 3), flag=wx.EXPAND|wx.RIGHT, border=10)

        row+=1
        bridge_port_label = wx.StaticText(self.panel, label="Port")
        sizer.Add(bridge_port_label, pos=(row, 0), flag=wx.LEFT, border=10)

        self.bridge_port = wx.TextCtrl(self.panel)
        self.bridge_port.SetToolTip(wx.ToolTip("This would normally be the 2nd argument passed to open_serial. " \
                                               "On Windows, the port is a zero-based list (Ex: 0 for COM1). " \
                                               "On Linux, the port will typically be a string (Ex:/dev/ttys1)."))
        sizer.Add(self.bridge_port, pos=(row, 1), span=(1, 3), flag=wx.EXPAND|wx.RIGHT, border=10)

        row+=1
        line = wx.StaticLine(self.panel)
        sizer.Add(line, pos=(row, 0), span=(1, 4), flag=wx.EXPAND|wx.BOTTOM, border=10)

        ####################################################
        # Add Crypto Options
        row+=1
        header_text = wx.StaticText(self.panel, label="Encryption Configuration")
        header_text.SetFont(header_font)
        sizer.Add(header_text, pos=(row, 0), span=(1,4), flag=wx.LEFT, border=10)

        row+=1
        crypto_type_label = wx.StaticText(self.panel, label="Encryption Type")
        sizer.Add(crypto_type_label, pos=(row, 0), flag=wx.LEFT, border=10)

        self.crypto_type = wx.ComboBox(self.panel, choices=CRYPTO_TYPES.keys(), style=wx.CB_READONLY|wx.CB_DROPDOWN)
        self.crypto_type.SetToolTip(wx.ToolTip("This represents the value saved in NV_AES128_ENABLE_ID"))
        self.crypto_type.SetValue("None")
        sizer.Add(self.crypto_type, pos=(row, 1), span=(1, 3), flag=wx.EXPAND|wx.RIGHT, border=10)

        row+=1
        crypto_key_label = wx.StaticText(self.panel, label="Encryption Key")
        sizer.Add(crypto_key_label, pos=(row, 0), flag=wx.LEFT, border=10)

        self.crypto_key = wx.TextCtrl(self.panel)
        self.crypto_key.SetToolTip(wx.ToolTip("16 character encryption key that represents the value saved in NV_AES128_KEY_ID. " \
                                              "This is not required when the encryption type is 'None'"))
        sizer.Add(self.crypto_key, pos=(row, 1), span=(1, 3), flag=wx.EXPAND|wx.RIGHT, border=10)

        row+=1
        line = wx.StaticLine(self.panel)
        sizer.Add(line, pos=(row, 0), span=(1, 4), flag=wx.EXPAND|wx.BOTTOM, border=10)

        ####################################################
        # Add Upgrade Information
        row+=1
        header_text = wx.StaticText(self.panel, label="Upgrade Information")
        header_text.SetFont(header_font)
        sizer.Add(header_text, pos=(row, 0), span=(1,4), flag=wx.LEFT, border=10)

        ####################################################
        # Add Address Field
        row+=1
        target_label = wx.StaticText(self.panel, label="Target Address (Ex: AA.BB.CC)")
        sizer.Add(target_label, pos=(row, 0), flag=wx.LEFT, border=10)

        self.target_addr = wx.TextCtrl(self.panel)
        self.target_addr.SetToolTip(wx.ToolTip("Address of the node that should be upgraded. "\
                                              "Valid formats are AA.BB.CC or AABBCC"))
        sizer.Add(self.target_addr, pos=(row, 1), span=(1, 3), flag=wx.LEFT|wx.EXPAND|wx.RIGHT, border=10)

        ####################################################
        # Add SFI File Picker
        row+=1
        self.sfi_file = filebrowsebutton.FileBrowseButton(self.panel,
                                    labelText="SFI File",
                                    fileMask="SNAP Firmware Image (*.sfi)|*.sfi|All Files (*.*)|*.*",
                                    fileMode=wx.OPEN,
                                    toolTip="Type filename or click browse to choose file. " \
                                            "This file should be a *.SPI firmware image for " \
                                            "the platform running on the target node.")

        sizer.Add(self.sfi_file, pos=(row, 0), span=(1,4), flag=wx.LEFT|wx.EXPAND|wx.RIGHT, border=10)

        row+=1
        line = wx.StaticLine(self.panel)
        sizer.Add(line, pos=(row, 0), span=(1, 4), flag=wx.EXPAND|wx.BOTTOM, border=10)

        ####################################################
        # Add a status bar
        row+=1
        self.progress_bar = wx.Gauge(self.panel, range=1000) #Because Range is an integer, using 1000 lets us get more granular
        sizer.Add(self.progress_bar, pos=(row, 0), span=(1,4), flag=wx.LEFT|wx.EXPAND|wx.RIGHT, border=10)

        row+=1
        self.status_text = wx.StaticText(self.panel, label="")

        sizer.Add(self.status_text, pos=(row, 0), span=(1,4), flag=wx.LEFT, border=10)

        ####################################################
        # Add the Start / Cancel button
        row+=1
        self.upgrade_button = wx.Button(self.panel, label="Start Upgrade")
        self.upgrade_button.Bind(wx.EVT_BUTTON, self.on_upgrade_button_clicked)
        sizer.Add(self.upgrade_button, pos=(row, 0), span=(1,4), border=5, flag=wx.ALIGN_CENTER|wx.ALIGN_CENTER_VERTICAL)

        ####################################################
        # Attach the sizer to the panel
        sizer.AddGrowableCol(2) #Column 2 will take up extra space if it is available
        self.panel.SetSizer(sizer)


    def get_upgrade_addr(self):
        """Get the upgrade addr from the GUI in the SNAP address format"""
        addr = self.target_addr.GetValue()
        if len(addr) == 6: #AABBCC
            return binascii.unhexlify(addr)
        elif len(addr) == 8 and (addr[2] == '.') and addr[5] == '.': #AA.BB.CC
            #Make sure it fits the pattern, then strip dots for conversion
            temp = addr[0:2] + addr[3:5] + addr[6:8]
            return binascii.unhexlify(temp)
        else:
            return None

    def restore_original_state(self):
        """Restore everything to the original state if an upgrade has failed or succeeded"""
        self.upgrade_in_progress = False
        self.progress_bar.SetValue(0)
        self.upgrade_button.SetLabel("Start Upgrade")
        self.enable_inputs()

    ###########################
    # GUI Helper functions
    def get_form_error(self):
        """Returns the next form error or None if there are no issues"""
        if not self.bridge_type.GetValue():
            return "You must provide a bridge type!"

        if not self.bridge_port.GetValue():
            return "You must provide a bridge port!"

        if not self.crypto_type.GetValue():
            return "You must provide an encryption type!"

        if CRYPTO_TYPES[self.crypto_type.GetValue()] != snap.ENCRYPTION_TYPE_NONE:
            if not self.crypto_key.GetValue():
                return "You must provide an encryption key!"

            if len(self.crypto_key.GetValue()) != 16:
                return "The provided encryption key is not the correct length (16 characters)!"

        if not self.target_addr.GetValue():
            return "You must provide a target address!"

        # Make sure the address is a valid format
        try:
            if not self.get_upgrade_addr():
                return "The target address must be specified in the form fo AABBCC or AA.BB.CC!"
        except TypeError, exc:
            return "The target address contains invalid characters!"

        if not self.sfi_file.GetValue():
            return "You must provide an SFI file!"

        return None

    def disable_inputs(self):
        """Disable all input fields"""
        for child in self.panel.GetChildren():
            if (isinstance(child, wx.TextCtrl) or
                isinstance(child, wx.ComboBox) or
                isinstance(child, filebrowsebutton.FileBrowseButton) or
                isinstance(child, wx.Button)):
               child.Disable()

    def enable_inputs(self):
        """Enable all input fields"""
        for child in self.panel.GetChildren():
            if (isinstance(child, wx.TextCtrl) or
                isinstance(child, wx.ComboBox) or
                isinstance(child, filebrowsebutton.FileBrowseButton) or
                isinstance(child, wx.Button)):
               child.Enable()

    #################
    # Event hooks
    def on_upgrade_button_clicked(self, event):
        """Called when the upgrade button is clicked

        This could either be used to start a new upgrade or cancel an existing upgrade.

        After clicking the button, the application will set the SNAP Connect instance
        to use the provided encryption parameters to configure SNAP Connect and attempt
        to connect to the serial bridge. When the bridge is successfully opened the upgrade
        will begin.  While upgrading, all inputs are locked to avoid changes.
        """
        if not self.upgrade_in_progress:
            # If no upgrade is in progress, we need to start the upgrade process
            # First, validate all of the fields, there's no point in starting if we're missing input
            error = self.get_form_error()

            if error:
                self.set_error(error)
                return
            else:
                self.set_status("Connecting to bridge...")

            # Disable all of the fields, we don't want to change anything mid upgrade
            self.disable_inputs()

            # Start connecting to the bridge, we'll kick off the upgrade if we can connect
            def connect_to_bridge():
                log.info("Connecting to the bridge")

                # Set the encryption type
                try:
                    self.comm.save_nv_param(snap.NV_AES128_ENABLE_ID, CRYPTO_TYPES[self.crypto_type.GetValue()])
                    self.comm.save_nv_param(snap.NV_AES128_KEY_ID, self.crypto_key.GetValue())
                except Exception, exc:
                    self.set_error("Unable to set the encryption type")
                    self.restore_original_state()
                    return

                # Start connecting to the bridge
                try:
                    # Convert the port value to the correct type
                    # Some operating systems expect a string for this argument, while others expect integers
                    serial_port = self.bridge_port.GetValue()
                    if serial_port.isdigit():
                        serial_port = int(serial_port)

                    serial_type = SERIAL_PORT_TYPES[self.bridge_type.GetValue()]

                    # If this is not the first attempt at starting an upgrade, close the previous connection
                    snap.Snap.close_all_serial()

                    # After calling open_serial, we are guaranteed a call to the serial opened hook, even for a failure
                    self.comm.open_serial(serial_type, serial_port)
                except Exception, exc:
                    self.set_error("Unable to open bridge connection")
                    self.restore_original_state()
                    return

            log.info("Scheduling connection to the bridge")
            self.comm.scheduler.schedule(0, connect_to_bridge)
        else:
            # If an upgrade is in progress, this is a Cancel operation
            # Disable the cancel button
            self.upgrade_button.Disable()

            # Start canceling the upgrade
            def cancel_upgrade():
                # After telling an upgrade to cancel, the upgrade complete hook will be fired
                # if the cancel succeeds or the upgrade completes anyway
                cancel_addr = self.get_upgrade_addr()
                log.info("Canceling upgrade for address %s"%binascii.hexlify(cancel_addr))
                self.comm.cancel_upgrade(cancel_addr)
            self.comm.scheduler.schedule(0, cancel_upgrade)

    ####################
    # Status Functions
    def set_status(self, message):
        """Set a new status message"""
        self.status_text.SetForegroundColour('black')
        self.status_text.SetLabel(message)

    def set_error(self, message):
        """Set a new status message"""
        self.status_text.SetForegroundColour('red')
        self.status_text.SetLabel(message)

    def set_success(self, message):
        """Set a new status message"""
        self.status_text.SetForegroundColour('blue')
        self.status_text.SetLabel(message)

    ######################
    # SNAP Connect Hooks
    def _upgrade_complete_hook(self, addr, status, message):
        """Hook called when an OTA firmware upgrade has completed"""
        log.info("Upgrade Complete: %r %r %r"%(addr, status, message))
        if status == snap.OTA_PROGRESS_COMPLETE:
            self.progress_bar.SetValue(1000) #Complete the progress bar
            self.set_success("Upgrade Complete for %s"%(binascii.hexlify(addr)))
        elif status == snap.OTA_PROGRESS_CANCELED:
            self.set_status("Upgrade Canceled for %s"%(binascii.hexlify(addr)))
        else:
            if message is None:
                message = ""
            self.set_error("Upgrade Failed for %s. %s"%(binascii.hexlify(addr), message))

        self.restore_original_state()

    def _upgrade_status_hook(self, addr, percent_complete):
        """Hook called when the status has changed during an OTA firmware upgrade"""
        log.debug("Upgrade Status: %r %r"%(addr, percent_complete))
        self.progress_bar.SetValue(int(percent_complete*10)) #Turn a percentage into an integer with a max of 1000


    def _serial_open_hook(self, type, port, addr):
        """Hook called when the serial bridge connection has opened"""
        log.info("Serial connection opened (type=%r, port=%r, addr=%r)"%(type,port,addr))
        if addr:
            # Kick off the upgrade
            self.set_success("Connected to bridge %s - Upgrade in progress"%(binascii.hexlify(addr)))
            self.upgrade_in_progress = True
            self.upgrade_button.SetLabel("Cancel Upgrade")
            self.upgrade_button.Enable()
            upgrade_addr = self.get_upgrade_addr()
            sfi_file = self.sfi_file.GetValue()
            log.info("Starting upgrade of %s to %s"%(binascii.hexlify(upgrade_addr), sfi_file))
            self.comm.upgrade_firmware(upgrade_addr, sfi_file)
        else:
            #We failed to communicate with the bridge, close out the connection and display failure
            self.comm.close_serial(type, port)
            self.set_error("Unable to connect to the bridge")
            self.enable_inputs()

    ########################
    # SNAP Connect Polling
    def poll_snap(self, evt):
        """Poll the SNAP Connect instance from inside the applications event loop"""
        self.comm.poll()


class FirmwareUpgradeApp(wx.App):
    """Basic application that creates an instance of the Firmware Upgrade Frame and shows it"""
    def OnInit(self):
        upgrade_frame = FirmwareUpgradeFrame()
        upgrade_frame.Center()
        upgrade_frame.Show(True)
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        filename='FirmwareUpgrader.log')

    #Direct output to the console as well as a file
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)

    #Construct the application and start the main event loop
    app = FirmwareUpgradeApp(False)
    app.MainLoop()




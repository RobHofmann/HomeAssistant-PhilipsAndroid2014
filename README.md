# HomeAssistant-PhilipsAndroid2014
Custom component for Philips TV's running Android which are built between 2014 and 2016. Written in Python3 for Home Assistant.
NOTE: Credits fully go to SirGilbot which made this modification based on the original Philips HASS component.

I'll be trying to get this module available through HACS for easy installation.

Tested on:
* Philips 55PUS9109/12 (2014)
* Home-Assistant 
    - 0.95.x

 **If you are experiencing issues please be sure to provide details about your device, Home Assistant version and what exactly went wrong.**

**Sources used:**
 - https://community.home-assistant.io/t/philips-android-tv-component/17749/62 (CREDITS GO 100% TO THIS GUY)
 
## HACS
This component will be submitted to be added to HACS asap.

## Custom Component Installation
!!! PLEASE NOTE !!!: Don't use this method if you are using HACS.
1. Copy the custom_components folder to your own hassio /config folder.

2. In the root of your /config folder, create a file called mediaplayers.yaml

   ```yaml
    - platform: philips_2014
      name: My Philips TV
      host: <ip of your TV>
      mac: <mac address of your TV>
   ```

3. In your configuration.yaml add the following:
  
   ```yaml
   media_player: !include mediaplayers.yaml
   ```

4. OPTIONAL: Add info logging to this component (to see if/how it works)
  
   ```yaml
   logger:
     default: error
     logs:
       custom_components.philips_2014: debug
       custom_components.philips_2014.media_player: debug
   ```

5. Restart Home Assistant and enjoy!
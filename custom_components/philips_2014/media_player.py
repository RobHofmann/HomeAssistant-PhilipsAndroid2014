"""
Media Player component to integrate TVs exposing the Joint Space API.
Updated to support Android-based Philips TVs manufactured from 2014 but before 2016.
"""
import homeassistant.helpers.config_validation as cv
import argparse
import json
import random
import requests
import string
import sys
import voluptuous as vol
import time
import wakeonlan

from base64 import b64encode,b64decode
from Crypto.Hash import SHA, HMAC
from datetime import timedelta, datetime
from homeassistant.components.media_player import (PLATFORM_SCHEMA, SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP, MediaPlayerDevice)
from homeassistant.const import (
	CONF_HOST, CONF_MAC, CONF_NAME, CONF_USERNAME, CONF_PASSWORD, STATE_OFF, STATE_ON, STATE_UNKNOWN)
from homeassistant.util import Throttle
from requests.auth import HTTPDigestAuth

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

SUPPORT_PHILIPS_2014 = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_VOLUME_STEP | SUPPORT_VOLUME_MUTE

DEFAULT_DEVICE = 'default'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_MAC = 'aa:aa:aa:aa:aa:aa'
DEFAULT_USER = 'user'
DEFAULT_PASS = 'pass'
DEFAULT_NAME = 'Philips TV'
BASE_URL = 'http://{0}:1925/5/{1}'
TIMEOUT = 5.0
CONNFAILCOUNT = 5

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
	vol.Required(CONF_MAC, default=DEFAULT_MAC): cv.string,
	vol.Optional(CONF_USERNAME, default=DEFAULT_USER): cv.string,
	vol.Optional(CONF_PASSWORD, default=DEFAULT_PASS): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
	"""Set up the Philips 2016+ TV platform."""
	name = config.get(CONF_NAME)
	host = config.get(CONF_HOST)
	mac = config.get(CONF_MAC)
	user = config.get(CONF_USERNAME)
	password = config.get(CONF_PASSWORD)
	tvapi = PhilipsTVBase(host, mac, user, password)
	add_devices([PhilipsTV(tvapi, name)])

class PhilipsTV(MediaPlayerDevice):
	"""Representation of a 2014-2015 Philips TV exposing the JointSpace API but not authentication."""

	def __init__(self, tv, name):
		"""Initialize the TV."""
		self._tv = tv
		self._name = name
		self._state = STATE_UNKNOWN
		self._min_volume = None
		self._max_volume = None
		self._volume = None
		self._muted = False
		self._connfail = 0

	@property
	def name(self):
		"""Return the device name."""
		return self._name

	@property
	def should_poll(self):
		"""Device should be polled."""
		return True

	@property
	def supported_features(self):
		"""Flag media player features that are supported."""
		return SUPPORT_PHILIPS_2014

	@property
	def state(self):
		"""Get the device state. An exception means OFF state."""
		return self._state

	@property
	def volume_level(self):
		"""Volume level of the media player (0..1)."""
		return self._volume

	@property
	def is_volume_muted(self):
		"""Boolean if volume is currently muted."""
		return self._muted

	def turn_on(self):
		"""Turn on the device."""
		i = 0
		while ((not self._tv.on) and (i < 15)):
			self._tv.wol()
			self._tv.sendKey('Standby')
			time.sleep(2)
			i += 1
		if self._tv.on:
			self._state = STATE_OFF

	def turn_off(self):
		"""Turn off the device."""
		i = 0
		while ((self._tv.on) and (i < 15)):
			self._tv.sendKey('Standby')	
			time.sleep(0.5)
			i += 1
		if not self._tv.on:
			self._state = STATE_OFF

	def volume_up(self):
		"""Send volume up command."""
		self._tv.sendKey('VolumeUp')
		if not self._tv.on:
			self._state = STATE_OFF

	def volume_down(self):
		"""Send volume down command."""
		self._tv.sendKey('VolumeDown')
		if not self._tv.on:
			self._state = STATE_OFF

	def mute_volume(self, mute):
		"""Send mute command."""
		self._tv.sendKey('Mute')
		if not self._tv.on:
			self._state = STATE_OFF

	@property
	def media_title(self):
		"""Title of current playing media."""
		return None

	@Throttle(MIN_TIME_BETWEEN_UPDATES)
	def update(self):
		"""Get the latest data and update device state."""
		self._tv.update()
		self._min_volume = self._tv.min_volume
		self._max_volume = self._tv.max_volume
		self._volume = self._tv.volume
		self._muted = self._tv.muted
		if self._tv.on:
			self._state = STATE_ON
		else:
			self._state = STATE_OFF

class PhilipsTVBase(object):
	def __init__(self, host, mac, user, password):
		self._host = host
		self._mac = mac
		self._user = user
		self._password = password
		self._connfail = 0
		self.on = None
		self.name = None
		self.min_volume = None
		self.max_volume = None
		self.volume = None
		self.muted = None
		self.sources = None
		self.source_id = None
		self.channels = None
		self.channel_id = None

	def _getReq(self, path):
		try:
			if self._connfail:
				self._connfail -= 1
				return None
			resp = requests.get(BASE_URL.format(self._host, path), timeout=TIMEOUT)
			self.on = True
			return json.loads(resp.text)
		except requests.exceptions.RequestException as err:
			self._connfail = CONNFAILCOUNT
			self.on = False
			return None

	def _postReq(self, path, data):
		try:
			if self._connfail:
				self._connfail -= 1
				return False
			resp = requests.post(BASE_URL.format(self._host, path), data=json.dumps(data))
			self.on = True
			if resp.status_code == 200:
				return True
			else:
				return False
		except requests.exceptions.RequestException as err:
			self._connfail = CONNFAILCOUNT
			self.on = False
			return False

	def update(self):
		self.getName()
		self.getAudiodata()

	def getName(self):
		r = self._getReq('system/name')
		if r:
			self.name = r['name']

	def getAudiodata(self):
		audiodata = self._getReq('audio/volume')
		if audiodata:
			self.min_volume = int(audiodata['min'])
			self.max_volume = int(audiodata['max'])
			self.volume = audiodata['current']
			self.muted = audiodata['muted']
		else:
			self.min_volume = None
			self.max_volume = None
			self.volume = None
			self.muted = None

	def setVolume(self, level):
		if level:
			if self.min_volume != 0 or not self.max_volume:
				self.getAudiodata()
			if not self.on:
				return
			try:
				targetlevel = int(level)
			except ValueError:
				return
			if targetlevel < self.min_volume + 1 or targetlevel > self.max_volume:
				return
			self._postReq('audio/volume', {'current': targetlevel, 'muted': False})
			self.volume = targetlevel

	def sendKey(self, key):
		self._postReq('input/key', {'key': key})

	def wol(self):
		wakeonlan.send_magic_packet(self._mac)
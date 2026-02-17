"""Fellow object to interact with Aiden brewer."""
import logging
import re
import requests
from difflib import SequenceMatcher
from .profile import CoffeeProfile
from .schedule import CoffeeSchedule
from pydantic import ValidationError
from urllib3.util import Retry
from requests.adapters import HTTPAdapter


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

    
class FellowAiden:

    """Fellow object to interact with Aiden brewer."""

    LOGGER_NAME = "custom_components.fellow.fellow_aiden.api"
    INTERVAL = 0.5
    BASE_URL = 'https://l8qtmnc692.execute-api.us-west-2.amazonaws.com/v1'
    API_AUTH = '/auth/login'
    API_DEVICES = '/devices'
    API_DEVICE = '/devices/{id}'
    API_SCHEDULES = '/devices/{id}/schedules'
    API_SCHEDULE = '/devices/{id}/schedules/{sid}'
    API_PROFILES = '/devices/{id}/profiles'
    API_PROFILE = '/devices/{id}/profiles/{pid}'
    API_PROFILE_SHARE = '/devices/{id}/profiles/{pid}/share'
    API_SHARED_PROFILE = '/shared/{bid}'
    HEADERS = {
        'User-Agent': 'Fellow/5 CFNetwork/1568.300.101 Darwin/24.2.0'
    }
    SERVER_SIDE_PROFILE_FIELDS = [
        'id',
        'createdAt',
        'deletedAt',
        'lastUsedTime',
        'sharedFrom',
        'isDefaultProfile',
        'instantBrew',
        'folder',
        'duration',
        'lastGBQuantity'
    ]

    def __init__(self, email, password):
        """Start of self."""
        self._log = self._logger()
        self._auth = False
        self._token = None
        self._refresh = None
        self._email = email
        self._password = password
        self._device_config = None
        self._brewer_id = None
        self._profiles = None
        self._schedules = None

        # Create instance-level session so each FellowAiden instance maintains its own auth state
        self._session = requests.Session()
        retries = Retry(
            total=3,
            status_forcelist=[408, 500, 501, 502, 503, 504],
        )
        self._session.mount('https://', HTTPAdapter(max_retries=retries))

        self.__auth(fetch_device=True)
        
    def _logger(self):
        """Create a logger to be used between processes.

        :returns: Logging instance.
        """
        return logging.getLogger(self.LOGGER_NAME)
        
    def _parse_response(self, response):
        """Parse a response body as JSON, falling back to raw text."""
        try:
            return response.json()
        except ValueError:
            text = response.text.strip()
            if text:
                return {"raw": text}
            return {}

    def _ensure_success(self, response, action):
        """Raise a descriptive error when a response is not HTTP 2xx."""
        if 200 <= response.status_code < 300:
            return

        parsed = self._parse_response(response)
        raise Exception(f"{action} failed ({response.status_code}): {parsed}")

    def _request_with_reauth(self, method, url, **kwargs):
        """Send a request and retry once after refreshing auth on HTTP 401."""
        response = self._session.request(method, url, **kwargs)
        if response.status_code == 401:
            self._log.warning("Unauthorized response received. Attempting to reauthenticate...")
            self.__auth(fetch_device=False)
            response = self._session.request(method, url, **kwargs)
        return response

    def __auth(self, fetch_device=False):
        self._log.debug("Authenticating user")
        auth = {"email": self._email, "password": self._password}
        self._session.headers.update(self.HEADERS)
        login_url = self.BASE_URL + self.API_AUTH
        response = self._session.post(login_url, json=auth, headers=self.HEADERS)
        if response.status_code in (400, 401, 403):
            raise Exception("Email or password incorrect.")

        self._ensure_success(response, "Authentication")
        parsed = self._parse_response(response)
        self._log.debug(parsed)
        if "accessToken" not in parsed or "refreshToken" not in parsed:
            raise Exception(f"Authentication response missing tokens: {parsed}")

        self._log.debug("Authentication successful")
        self._token = parsed["accessToken"]
        self._refresh = parsed["refreshToken"]
        self._session.headers.update({"Authorization": "Bearer " + self._token})
        self._auth = True
        if fetch_device:
            self.__device()
        
    def __device(self):
        self._log.debug("Fetching device for account")
        device_url = self.BASE_URL + self.API_DEVICES
        response = self._request_with_reauth("get", device_url, params={"dataType": "real"})
        self._ensure_success(response, "Device fetch")

        parsed = self._parse_response(response)
        self._log.debug(parsed)
        if not isinstance(parsed, list):
            raise Exception(f"Unexpected device response payload: {parsed}")
        if not parsed:
            raise Exception("No Fellow Aiden devices found for this account.")

        first_device = parsed[0]
        if not isinstance(first_device, dict):
            raise Exception(f"Unexpected device payload type: {first_device}")

        brewer_id = first_device.get("id")
        if not brewer_id:
            raise Exception(f"Device response missing required id field: {first_device}")

        self._device_config = first_device
        self._brewer_id = brewer_id

        self._profiles = None
        self._schedules = None

        self._log.debug("Brewer ID: %s" % self._brewer_id)
        self._log.debug("Device and profile information set")

    @property
    def profiles(self):
        if self._profiles is None:
            self._log.debug("Fetching profiles")
            profiles_url = self.BASE_URL + self.API_PROFILES.format(id=self._brewer_id)
            response = self._request_with_reauth("get", profiles_url)
            self._ensure_success(response, "Profile fetch")

            parsed = self._parse_response(response)
            if not isinstance(parsed, list):
                raise Exception(f"Unexpected profiles response payload: {parsed}")

            self._log.debug(parsed)
            self._profiles = parsed
        
        return self._profiles
    
    @property
    def schedules(self):
        if self._schedules is None:
            self._log.debug("Fetching schedules")
            schedules_url = self.BASE_URL + self.API_SCHEDULES.format(id=self._brewer_id)
            response = self._request_with_reauth("get", schedules_url)
            self._ensure_success(response, "Schedule fetch")

            parsed = self._parse_response(response)
            if not isinstance(parsed, list):
                raise Exception(f"Unexpected schedules response payload: {parsed}")

            self._log.debug(parsed)
            self._schedules = parsed
        
        return self._schedules


    def __get_profile_ids(self):
        """Return a list of profile IDs."""
        return ["%s (%s)" % (profile["id"], profile["title"]) for profile in self.profiles]
    
    def __is_valid_profile_id(self, pid):
        """Check if a profile ID is valid."""
        for profile in self.profiles:
            if pid == profile["id"]:
                return True
        return False
    
    def __get_schedule_ids(self):
        """Return a list of schedule IDs."""
        return ["%s" % (schedule["id"]) for schedule in self.schedules]
    
    def __is_valid_schedule_id(self, sid):
        """Check if a schedule ID is valid."""
        for schedule in self.schedules:
            if sid == schedule["id"]:
                return True
        return False

    def parse_brewlink_url(self, link):
        """Extract profile information from a shared brew link."""
        self._log.debug("Parsing shared brew link")
        pattern = r'(?:.*?/p/)?([a-zA-Z0-9]+)/?$'
        match = re.search(pattern, link)
        if not match:
            raise ValueError("Invalid profile URL or ID format")
        brew_id = match.group(1)
        self._log.debug("Brew ID: %s" % brew_id)
        shared_url = self.BASE_URL + self.API_SHARED_PROFILE.format(bid=brew_id)
        response = self._request_with_reauth("get", shared_url)
        if response.status_code == 404:
            raise ValueError(f"Failed to fetch profile (ID: {brew_id})")

        self._ensure_success(response, f"Shared profile fetch (ID: {brew_id})")
        parsed = self._parse_response(response)
        if not isinstance(parsed, dict):
            raise ValueError(f"Unexpected shared profile payload for ID {brew_id}: {parsed}")

        for field in self.SERVER_SIDE_PROFILE_FIELDS:
            parsed.pop(field, None)
        self._log.debug("Profile fetched: %s" % parsed)
        return parsed
    
    def get_device_config(self, remote=False):
        """Return the current device config.

        :param remote: If True, force a new request to Fellow's API
                    to refresh the device config. Otherwise,
                    returns the cached config.
        """
        if remote:
            self.__device()
        return self._device_config

        
    def get_display_name(self):
        return self._device_config.get('displayName', None)
        
    def get_profiles(self):
        return self.profiles
    
    def get_schedules(self):
        return self.schedules
    
    def get_profile_by_title(self, title, fuzzy=False):
        for profile in self.profiles:
            if fuzzy:
                if similar(profile['title'].lower(), title.lower()) > 0.65:
                    return profile
            if profile['title'].lower() == title.lower():
                return profile
        return None
        
    def get_brewer_id(self):
        return self._brewer_id
        
    def create_profile(self, data):
        self._log.debug("Checking brew profile: %s" % data)
        try:
            CoffeeProfile.model_validate(data)
        except ValidationError as err:
            self._log.error("Brew profile format was invalid: %s" % err)
            raise ValueError(f"Brew profile format was invalid: {err}") from err
        
        if 'id' in data.keys():
            raise Exception("Candidate profiles must be free of server derived fields.")

        self._log.debug("Brew profile passed checks")
        profile_url = self.BASE_URL + self.API_PROFILES.format(id=self._brewer_id)
        response = self._request_with_reauth("post", profile_url, json=data)
        self._ensure_success(response, "Profile creation")

        parsed = self._parse_response(response)
        if "id" not in parsed:
            raise Exception("Error in processing: %s" % parsed)

        self.__device()  # Refreshed profiles this way
        self._log.debug("Brew profile created: %s" % parsed)
        return parsed
    
    def update_profile(self, profile_id, data):
        """Update an existing profile by ID."""
        self._log.debug(f"Updating brew profile {profile_id}: {data}")
        
        # Validate the profile data
        try:
            CoffeeProfile.model_validate(data)
        except ValidationError as err:
            self._log.error("Brew profile format was invalid: %s" % err)
            raise ValueError(f"Brew profile format was invalid: {err}") from err
        
        # Check if profile exists
        if not self.__is_valid_profile_id(profile_id):
            message = f"Profile with ID {profile_id} does not exist. Valid profiles: {self.__get_profile_ids()}"
            raise Exception(message)
        
        # Remove any server-side fields that might be in the data
        for field in self.SERVER_SIDE_PROFILE_FIELDS:
            if field in data:
                data.pop(field, None)
        
        # Use PATCH to update the profile
        update_url = self.BASE_URL + self.API_PROFILE.format(id=self._brewer_id, pid=profile_id)
        self._log.debug(f"Update URL: {update_url}")
        response = self._request_with_reauth("patch", update_url, json=data)
        self._ensure_success(response, f"Profile update ({profile_id})")
        
        self.__device()  # Refresh profiles
        self._log.debug(f"Profile {profile_id} updated successfully")
        return True
    
    def create_schedule(self, data):
        self._log.debug("Checking schedule: %s" % data)
        try:
            CoffeeSchedule.model_validate(data)
        except ValidationError as err:
            self._log.error("Brew schedule format was invalid: %s" % err)
            raise ValueError(f"Brew schedule format was invalid: {err}") from err
        
        if 'id' in data.keys():
            raise Exception("Candidate schedules must be free of server derived fields.")

        self._log.debug("Brew schedule passed checks")
        schedule_url = self.BASE_URL + self.API_SCHEDULES.format(id=self._brewer_id)
        response = self._request_with_reauth("post", schedule_url, json=data)
        self._ensure_success(response, "Schedule creation")

        parsed = self._parse_response(response)
        if "id" not in parsed:
            message = parsed.get("message", "Unable to get error message.")
            if "Profile could not be found" in message:
                message += "Valid profiles: %s" % self.__get_profile_ids()
            raise Exception("Error in processing: %s" % message)

        self.__device()  # Refreshed schedules this way
        self._log.debug("Brew schedule created: %s" % parsed)
        return parsed

    def create_profile_from_link(self, link):
        """Create a profile from a shared brew link."""
        self._log.debug("Creating profile from link")
        data = self.parse_brewlink_url(link)
        return self.create_profile(data)
    
    def generate_share_link(self, pid):
        """Generate a share link for a profile."""
        self._log.debug("Generating share link")
        share_url = self.BASE_URL + self.API_PROFILE_SHARE.format(id=self._brewer_id, pid=pid)
        self._log.debug("Share URL: %s" % share_url)
        response = self._request_with_reauth("post", share_url)
        self._ensure_success(response, f"Share link generation ({pid})")

        parsed = self._parse_response(response)
        if "link" not in parsed:
            raise Exception("Error in processing: %s" % parsed)

        self._log.debug("Share link generated: %s" % parsed)
        return parsed["link"]
        
    def delete_profile_by_id(self, pid):
        self._log.debug("Deleting profile")
        # Check is too slow with new lazy loading impelementation
        # if not self.__is_valid_profile_id(pid):
        #     message = "Profile does not exist. Valid profiles: %s" % (self.__get_profile_ids())
        #     raise Exception(message)
        delete_url = self.BASE_URL + self.API_PROFILE.format(id=self._brewer_id, pid=pid)
        self._log.debug(delete_url)
        response = self._request_with_reauth("delete", delete_url)
        self._ensure_success(response, f"Profile deletion ({pid})")

        self._log.debug("Profile deleted")
        return True
    
    def delete_schedule_by_id(self, sid):
        self._log.debug("Deleting schedule")
        if not self.__is_valid_schedule_id(sid):
            message = "Schedule does not exist. Valid schedules: %s" % (self.__get_schedule_ids())
            raise Exception(message)
        delete_url = self.BASE_URL + self.API_SCHEDULE.format(id=self._brewer_id, sid=sid)
        self._log.debug(delete_url)
        response = self._request_with_reauth("delete", delete_url)
        self._ensure_success(response, f"Schedule deletion ({sid})")

        self._log.debug("Schedule deleted")
        return True
    
    def adjust_setting(self, setting, value):
        patch_url = self.BASE_URL + self.API_DEVICE.format(id=self._brewer_id)
        self._log.debug("Patch URL: %s" % patch_url)
        response = self._request_with_reauth("patch", patch_url, json={setting: value})
        self._ensure_success(response, f"Device setting update ({setting})")
        return response.content
    
    def toggle_schedule(self, sid, enabled):
        if not self.__is_valid_schedule_id(sid):
            message = "Schedule does not exist. Valid schedules: %s" % (self.__get_schedule_ids())
            raise Exception(message)
        patch_url = self.BASE_URL + self.API_SCHEDULE.format(id=self._brewer_id, sid=sid)
        self._log.debug("Patch URL: %s" % patch_url)
        response = self._request_with_reauth("patch", patch_url, json={"enabled": enabled})
        self._ensure_success(response, f"Schedule toggle ({sid})")
        return True
        
    def authenticate(self):
        """
        Public method to reauthenticate the user.

        This allows external callers (like HA integration) to trigger
        reauthentication without accessing the private __auth method.
        """
        self._log.debug("Reauthenticating user via public method")
        self.__auth(fetch_device=True)

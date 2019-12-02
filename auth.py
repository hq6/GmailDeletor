import logging
import oauth2client
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from apiclient.discovery import build
# ...


# Path to client_secrets.json which should contain a JSON document that looks
# like the following.
#   {
#     "web": {
#       "client_id": "[[YOUR_CLIENT_ID]]",
#       "client_secret": "[[YOUR_CLIENT_SECRET]]",
#       "redirect_uris": [],
#       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#       "token_uri": "https://accounts.google.com/o/oauth2/token"
#     }
#   }
# Such a file can be downloaded from the API console after creating an application authorizing Gmail as discussed in the README.md.
#
CLIENTSECRETS_LOCATION = 'client_secret.json'

# Magic URI to get OAuth to display an authorization code on the screen instead
# of sending it to a non-existent website.
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

SCOPES = [
    'https://mail.google.com/',
]

class GetCredentialsException(Exception):
  """Error raised when an error occurred while retrieving credentials.

  Attributes:
    authorization_url: Authorization URL to redirect the user to in order to
                       request offline access.
  """

  def __init__(self, authorization_url):
    """Construct a GetCredentialsException."""
    self.authorization_url = authorization_url

class CodeExchangeException(GetCredentialsException):
  """Error raised when a code exchange has failed."""

def exchange_code(authorization_code):
  """Exchange an authorization code for OAuth 2.0 credentials.

  Args:
    authorization_code: Authorization code to exchange for OAuth 2.0
                        credentials.
  Returns:
    oauth2client.client.OAuth2Credentials instance.
  Raises:
    CodeExchangeException: an error occurred.
  """
  flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
  flow.redirect_uri = REDIRECT_URI
  try:
    credentials = flow.step2_exchange(authorization_code)
    return credentials
  except FlowExchangeError, error:
    logging.error('An error occurred: %s', error)
    raise CodeExchangeException(None)

def get_authorization_url(email_address, state = None):
  """Retrieve the authorization URL, which is presented to the user to ask them
  to authenticate.

  Args:
    email_address: User's e-mail address.
    state: State for the authorization URL.
  Returns:
    Authorization URL to redirect the user to.
  """
  flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
  flow.params['access_type'] = 'offline'
  flow.params['approval_prompt'] = 'force'
  flow.params['user_id'] = email_address
  flow.params['state'] = state
  return flow.step1_get_authorize_url(REDIRECT_URI)


def load_or_get_credentials():
  """
  Try to read credentials fro a file called `credentials.json` in the current
  directory. If this file does not exist, ask the user to authenticate.
  """
  try:
    with open("credentials.json") as cred_json:
      return oauth2client.client.Credentials.new_from_json(cred_json.read())
  except Exception as e:
    print e
    email = raw_input("No credentials.json found. Please enter your email address: ").strip()
    print "Please visit the following URL and paste one-time code here"
    print get_authorization_url(email)
    auth_code = raw_input("Authorization Code: ").strip()
    credentials = exchange_code(auth_code)

    # Save the credentials
    with open("credentials.json", "w") as cred_json:
      cred_json.write(credentials.to_json())

    return credentials

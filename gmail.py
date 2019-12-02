"""Get a list of Messages from the user's mailbox.
"""

from apiclient import errors
import auth

from time import sleep

################################################################################
# Create a service for actual use
from apiclient.discovery import build
import httplib2

def build_service(credentials):
   """Build a Gmail service object.

   Args:
           credentials: OAuth 2.0 credentials.

   Returns:
           Gmail service object.
   """
   http = httplib2.Http()
   http = credentials.authorize(http)
   return build('gmail', 'v1', http=http)
################################################################################

# This class wraps the Gmail API functions to manipulate messages listed below.
# https://developers.google.com/gmail/api/v1/reference/users/messages/
#
# It additional provides two higher-level functions to improve useability: View
# and AutoDelete.
class Gmail:
  def __init__(self):
    """
    Constructor. This function attempts to authorize the Gmail API using OAuth.
    To avoid the need to trust anyone except oneself with Gmail credentials,
    every user of this class should create their own application in the Google
    developer console and enable the Gmail APIs.

    https://console.cloud.google.com/apis/api/gmail.googleapis.com/credentials

    Be respectful of the API limits here:
    https://developers.google.com/gmail/api/v1/reference/quota

    """
    # service: Authorized Gmail API service instance.
    self.service = build_service(auth.load_or_get_credentials())

    # user_id: User's email address. The special value "me"
    # can be used to indicate the authenticated user.
    self.user_id = "me"

  def search(self, query='', max_results=100):
    """
    List all messages of the user's mailbox matching the query.
    Arguments and return values are documented here:

    https://developers.google.com/gmail/api/v1/reference/users/messages/list

    """
    try:
      response = self.service.users().messages().list(userId=self.user_id,
                                                 q=query, maxResults=max_results).execute()
      messages = []
      if 'messages' in response:
        messages.extend(response['messages'])

      max_results -= len(messages)
      while 'nextPageToken' in response and max_results > 0:
        page_token = response['nextPageToken']
        response = self.service.users().messages().list(userId=self.user_id, q=query,
                                           pageToken=page_token, maxResults=max_results).execute()
        messages.extend(response['messages'])

      return messages
    except errors.HttpError, error:
      print 'An error occurred: %s' % error

  def get(self, message_id, format = 'full'):
    """
    Get detailed message with the specific ID. Arguments and return values are
    documented at
    https://developers.google.com/gmail/api/v1/reference/users/messages/get.

    This function should be called at a maximum of 50 QPS.
    """
    return self.service.users().messages().get(userId=self.user_id, id=message_id, format=format).execute()

  def view(self, query='', results_per_page=10, format='full'):
    """
    Show detailed messages matching a particular query in a paginated fashion.

    Args:
      query: The search string to find messages with.
      results_per_page: The number of results to display per page.
    """

    # Small function for displaying subject and snippet for one or more
    # messages.
    def displayMessages(messages):
      for message in messages:
        message = self.get(message["id"])
        headers = message["payload"]["headers"]
        for h in headers:
          if h["name"] == "Subject":
            print "Subject: " + h["value"]
            break
        print message["snippet"] + "\n"

    try:
      response = self.service.users().messages().list(userId=self.user_id,
                                                 q=query, maxResults=results_per_page).execute()
      if 'messages' not in response:
        print "No messages matched the query"
        return

      # Display estimate and first set of messages.
      print "Gmail estimates that %d messages matched the given query." % response["resultSizeEstimate"]
      displayMessages(response['messages'])

      while 'nextPageToken' in response:
        page_token = response['nextPageToken']
        if raw_input("Press Enter to view the next page of results, type S to stop: ") == "S":
          return
        response = self.service.users().messages().list(userId=self.user_id, q=query,
                                           pageToken=page_token, maxResults=results_per_page).execute()
        displayMessages(response['messages'])

    except errors.HttpError, error:
      print 'An error occurred: %s' % error

  def trash(self, query=None, max_results = 10):
    """
    Move all messages matching a particular query to the trash. Note that this
    operation is reversible via the Gmail UI.
    """
    if query:
      messages = self.search(query, max_results)
      for message in messages:
        self.service.users().messages().trash(userId=self.user_id,id=message["id"]).execute()

  def delete(self, query=None):
    """
    Permanently delete mesages one at a time. Based on Google's advertised
    limits, a maximum of 25 messages can be deleted per second using this
    function.
    """
    if query:
      messages = self.search(query, 1)
      for message in messages:
        self.service.users().messages().delete(userId=self.user_id,id=message["id"]).execute()

  # Fast deletion. Call at maximum 5 QPS.
  def batchDelete(self, query=None, max_results=50):
    """
    Permanently delete max_results messages. Based on Google's advertised
    limits, this function should be called at a maximum of 5 QPS. Google
    recommends setting max_results <= 50 for each call, but in practice it
    seems to work fine with max_results = 1000.
    """
    if query:
      messages = self.search(query, max_results)
      if len(messages) == 0: return 0
      ids = { 'ids': [str(d['id']) for d in messages] }
      self.service.users().messages().batchDelete(userId=self.user_id,body=ids).execute()
      return len(messages)
    print "No query provided. Aborting."
    return 0

  def autoDelete(self, query=None, silent=False):
    """
    Automatically permanently delete all email corresponding to a given query
    at an acceptable QPS.
    """
    num_deleted = self.batchDelete(query, 1000)
    while num_deleted > 0:
      if not silent:
        print "Just deleted %d messages" % num_deleted
      sleep(0.5)
      num_deleted = self.batchDelete(query, 1000)


# This object is useable from the Python interpreter for invoking command line
# options.
gmail = Gmail()

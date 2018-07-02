import sys
import json
import requests
import urllib
import splunk.rest as rest

from jira_helpers import get_jira_password

# creates outbound message from alert payload contents
# and attempts to send to the specified endpoint
def send_message(payload, sessionKey):
    config = payload.get('configuration')

    ISSUE_REST_PATH = "/rest/api/latest/issue"
    url = config.get('jira_url')
    jira_url = url + ISSUE_REST_PATH
    
    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), sessionKey)

    body = {
        "fields": {
            "project": {
                "key" : config.get('project_key')
            },
            "summary": config.get('summary'),
            "description": config.get('description'),
            "issuetype": {
                "name": config.get('issue_type')
            },
            "priority": {
                "name": config.get('priority')
            },
            "assignee": {
                "name": config.get('assignee')
            }
        } 
    }

    customfields = { k: v for k, v in config.iteritems() if k.startswith('customfield_') }

    for k,v in customfields.iteritems():
        body['fields'][k] = v

    # create outbound JSON message body
    data = json.dumps(body)

    # create outbound request object
    try:
        headers = {"Content-Type": "application/json"}
        result = requests.post(url=jira_url, data=data, headers=headers, auth=(username, password))
             
    except Exception, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        return False

    # Get Results
    resultJSON = result.json()
        
    # Fetch Jira issueKey
    issue_key = resultJSON["key"]

    # Fetch Alert Manager incident_id (param.incident_id)
    incident_id=config.get('incident_id')
    incident_key = getIncidentKey(incident_id, sessionKey)    

    setIncidentExternalReferenceId(issue_key, incident_key, sessionKey)

    setIncidentComment(incident_id, issue_key, sessionKey)

    # Fetch Alert Manager Comment and add to Issue
    comment = config.get('comment')
    if comment is not None:
        addIssueComment(comment, issue_key, payload, sessionKey)

def addIssueComment(comment, issue_key, payload, sessionKey):
    config = payload.get('configuration')

    ISSUE_REST_PATH = "/rest/api/latest/issue/%s/comment" % issue_key
    url = config.get('jira_url')
    jira_url = url + ISSUE_REST_PATH
    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), payload.get('session_key'))

    body = '{"body": "%s"}' % comment
    
    try:
        headers = {"Content-Type": "application/json"}
        result = requests.post(url=jira_url, data=body, headers=headers, auth=(username, password))

    except Exception, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        return False
    
def getIncidentKey(incident_id, sessionKey):
    query = '{"incident_id": "%s"}' % incident_id
    uri = '/servicesNS/nobody/alert_manager/storage/collections/data/incidents?query=%s' % urllib.quote(query)
        
    incident=getRestData(uri, sessionKey, output_mode='default')

    incident_key = incident[0]["_key"]

    return incident_key


def setIncidentExternalReferenceId(issue_key, incident_key, sessionKey):
    uri = '/servicesNS/nobody/alert_manager/storage/collections/data/incidents/%s' % incident_key
    
    incident = getRestData(uri, sessionKey, output_mode='default')

    incident['external_reference_id'] = issue_key

    getRestData(uri, sessionKey, json.dumps(incident))

def getRestData(uri, sessionKey, data = None, output_mode = 'json'):
    try:
        if data == None:
            if output_mode == 'default':
                serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey)
            else:
                serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, getargs={'output_mode': 'json'})
        else:
            if output_mode == 'default':
                serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, jsonargs=data)
            else:
                serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, jsonargs=data, getargs={'output_mode': 'json'})
    except:
        serverContent = None

    try:
        returnData = json.loads(serverContent)
    except:
        returnData = []

    return returnData


def setIncidentComment(incident_id, issue_key, sessionKey):

    uri = "/services/alert_manager/helpers"
    postargs = '{"action": "write_log_entry", "log_action": "comment", "origin": "externalworkflowaction", "incident_id": "%s", "comment": "Updated external_reference_id=%s"}' % (incident_id, issue_key)

    try:
        serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, postargs=json.loads(postargs), method='POST')
  
    except:
        print >> sys.stderr, "ERROR Unexpected error: %s" % e
        serverContent= None
    return
    

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:

            # retrieving message payload from splunk
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)

            sessionKey = payload.get('session_key')

            send_message(payload, sessionKey)
        except Exception, e:
            print >> sys.stderr, "ERROR Unexpected error: %s" % e
            sys.exit(3)
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

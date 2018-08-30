import sys
import json
import requests
import re
import urllib
import splunk.rest as rest

from jira_helpers import get_jira_password

def log(message):
    with open('/tmp/alert_manager-jira.log','a') as f:
        print >> f, message

# creates outbound message from alert payload contents
# and attempts to send to the specified endpoint
def send_message(payload, sessionKey):
    config = payload.get('configuration')

    ISSUE_REST_PATH = "/rest/api/latest/issue"
    url = config.get('jira_url')
    jira_url = url + ISSUE_REST_PATH
    
    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), sessionKey)

    body= {
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

    customfield_types = getCustomFieldTypes(payload, sessionKey)

    customfields = { k: v for k, v in config.iteritems() if k.startswith('customfield_') }

    for k,v in customfields.iteritems():
        
        if customfield_types.get(k) == "textfield":
            body['fields'][k] = v
        elif customfield_types.get(k) == "textarea":
            body['fields'][k] = v
        elif customfield_types.get(k) == "select":
            body['fields'][k] = { "value": v }
        elif customfield_types.get(k) == "multiselect":
            body['fields'][k] = [ {"value": v } ]

    # create outbound JSON message body
    data = json.dumps(body)

    # create outbound request object
    try:
        headers = {"Content-Type": "application/json"}
        result = requests.post(url=jira_url, data=data, headers=headers, auth=(username, password))

        if result.status_code>299:
            print >> sys.stderr, "ERROR Unable to open JIRA Ticket: http_status=%s http_response=%s" % (result.status_code, result.text)
            sys.exit(2)
                
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

def getCustomFieldTypes(payload, sessionKey):
    config = payload.get('configuration')
    project_key = config.get('project_key')

    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), sessionKey)
    
    FIELDS_REST_PATH = "/rest/api/latest/issue/createmeta?projectKeys=%s&expand=projects.issuetypes.fields&" % project_key
    url = config.get('jira_url')

    jira_fields_url = url + FIELDS_REST_PATH


    try:
        headers = {"Content-Type": "application/json"}
        result = requests.get(url=jira_fields_url, headers=headers, auth=(username, password))
        
        meta = result.json()

        customfield_types = {}
        for m in re.finditer('(?P<field>customfield_\d+).*?"custom": "(?P<fieldtype>\S+)"', json.dumps(meta), re.MULTILINE):
            fieldtype = m.group('fieldtype')
            fieldtype = fieldtype.split(":",1)[1]
            customfield_types[m.group('field')] = fieldtype

        return customfield_types

    except Exception, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        log(e)
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

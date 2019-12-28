import sys
import json
import requests
import re
import urllib
import os.path
import splunk.rest as rest
import splunk.appserver.mrsparkle.lib.util as util

dir = os.path.join(util.get_apps_dir(), 'SA-alert_manager-jira', 'bin', 'lib')
if not dir in sys.path:
    sys.path.append(dir)

from AlertManagerJiraLogger import *
from jira_helpers import get_jira_password

def send_message(payload, sessionKey):
    log.info('Starting send_massage')

    config = payload.get('configuration')

    ISSUE_REST_PATH = "/rest/api/latest/issue"
    url = config.get('jira_url')
    jira_url = url + ISSUE_REST_PATH
    
    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), sessionKey)

    log.debug("Payload %s:" % json.dumps(payload))

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

    log.debug("Customfields %s:" % customfields)

    for k,v in customfields.iteritems():

        log.debug("start")
        if customfield_types.get(k) == "textfield":
            log.debug("Customfield %s=%s" % (customfield_types.get(k), v))
            body['fields'][k] = v

        elif customfield_types.get(k) == "textarea":
            log.debug("Customfield %s=%s" % (customfield_types.get(k), v))
            body['fields'][k] = v

        elif customfield_types.get(k) == "select":
            log.debug("Customfield %s=%s" % (customfield_types.get(k), v))
            body['fields'][k] = { "value": v }

        elif customfield_types.get(k) == "multiselect":
            log.debug("Customfield %s=%s" % (customfield_types.get(k), v))
            body['fields'][k] = [ {"value": v } ]

        elif customfield_types.get(k) == "sd-customer-organizations":
            log.debug("Customfield %s=%s" % (customfield_types.get(k), v))
            orglist = map(int, v.split(","))
            body['fields'][k] = orglist

        else:
            log.warn("Customfield unhandled: key=%s value=%s" % (k, v))
            
    
    # create outbound JSON message body

    log.debug("Body: %s" % body)

    data = json.dumps(body)

    log.debug("Data: %s" % data)

    # create outbound request object
    try:
        headers = {"Content-Type": "application/json"}
        result = requests.post(url=jira_url, data=data, headers=headers, auth=(username, password))

        if result.status_code>299:
            log.error("Unable to open JIRA Ticket: http_status=%s http_response=%s" % (result.status_code, result.text))
            sys.exit(2)
        else:
            log.info("Incident creation result: %s" % result.text)

                
    except Exception, e:
        log.error("Error sending message: %s" % e)
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
    
    next_status = config.get('alert_manager_next_status')
    if next_status is not None:

        query = '{"incident_id": "%s"}' % incident_id
        uri = '/servicesNS/nobody/alert_manager/storage/collections/data/incidents?query=%s' % urllib.quote(query)
        
        incident=getRestData(uri, sessionKey, output_mode='default')
        previous_status = incident[0]["status"]

        setIncidentStatus(next_status, incident_key, sessionKey)
        setIncidentChangeHistory(incident_id, next_status, previous_status, sessionKey)

def addIssueComment(comment, issue_key, payload, sessionKey):
    config = payload.get('configuration')

    issue_rest_path = "/rest/api/latest/issue/%s/comment" % issue_key
    url = config.get('jira_url')
    jira_url = url + issue_rest_path
    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), payload.get('session_key'))

    body = '{"body": "%s"}' % comment
    
    try:
        headers = {"Content-Type": "application/json"}
        result = requests.post(url=jira_url, data=body, headers=headers, auth=(username, password))

    except Exception, e:
        log.error("ERROR Error sending message: %s" % e)
        return False        

def getCustomFieldTypes(payload, sessionKey):
    log.info("Start getCustomFieldTypes")
    config = payload.get('configuration')
    project_key = config.get('project_key')
    issue_type = config.get('issue_type')

    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), sessionKey)
    
    field_rest_query = "/rest/api/latest/issue/createmeta?projectKeys=%s&expand=projects.issuetypes.fields&issuetypeNames=%s" % (project_key, urllib.quote(issue_type))
    log.debug("getCustomFieldTypes field_rest_query=%s" % field_rest_query)

    url = config.get('jira_url')

    jira_fields_url = url + field_rest_query

    log.debug("jira_fields_url=%s" % jira_fields_url)

    try:
        headers = {"Content-Type": "application/json"}
        result = requests.get(url=jira_fields_url, headers=headers, auth=(username, password))
        
        meta = result.json()

        customfield_types = {}
        for m in re.finditer('(?P<field>customfield_\d+).*?"custom": "(?P<fieldtype>\S+)"', json.dumps(meta), re.MULTILINE):
            fieldtype = m.group('fieldtype')
            fieldtype = fieldtype.split(":",1)[1]
            customfield_types[m.group('field')] = fieldtype

        log.debug("customfield_types: %s" % customfield_types)
        return customfield_types

    except Exception, e:
        log.error("ERROR Error sending message: %s" % e)
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

def setIncidentStatus(status, incident_key, sessionKey):
    uri = '/servicesNS/nobody/alert_manager/storage/collections/data/incidents/%s' % incident_key
    
    incident = getRestData(uri, sessionKey, output_mode='default')

    incident['status'] = status

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

def setIncidentChangeHistory(incident_id, status, previous_status, sessionKey):

    user = payload.get('owner')

    uri = "/services/alert_manager/helpers"
    postargs = '{"action": "write_log_entry", "log_action": "change", "origin": "externalworkflowaction", "incident_id": "%s", "user": "%s", "status": "%s", "previous_status": "%s"}' % (incident_id, user, status, previous_status)

    try:
        serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, postargs=json.loads(postargs), method='POST')
  
    except:
        print >> sys.stderr, "ERROR Unexpected error: %s" % e
        serverContent= None
    return    
    
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        log = setupLogger('alert_manager-jira')

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

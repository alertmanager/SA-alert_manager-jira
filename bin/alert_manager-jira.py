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
    password = get_jira_password(payload.get('server_uri'), payload.get('session_key'))

    # create outbound JSON message body
    body = json.dumps({
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
    })

    # create outbound request object
    try:
        headers = {"Content-Type": "application/json"}
        result = requests.post(url=jira_url, data=body, headers=headers, auth=(username, password))
             
        
        print >>sys.stderr, "INFO Jira server HTTP status= %s" % result.text
        print >>sys.stderr, "INFO Jira server response: %s" % result.text
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

    with open('/tmp/out2.txt', 'w') as outfile2:
            outfile2.write(incident_key)       

    setIncidentExternalReferenceId(issue_key, incident_key, sessionKey)


    
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

    with open('/tmp/out3.txt', 'w') as outfile2:
            outfile2.write(uri)       

    #if "_user" in incident:
    #    del(incident["_user"])
    #if "_key" in incident:
    #    del(incident["_key"])

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
        #log.info("An error occurred or no data was returned from the server query.")
        serverContent = None

    #log.debug("serverResponse: %s" % serverResponse)
    #log.debug("serverContent: %s" % serverContent)
    try:
        returnData = json.loads(serverContent)
    except:
        #log.info("An error occurred or no data was returned from the server query.")
        returnData = []

    return returnData


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

# Alert Manager Jira Add-on

## Introduction

This add-on allows Splunk to create Jira issues an Jira Service Desk Rquests from Alert Manager https://splunkbase.splunk.com/app/2665/

When an Alert Manager Incident is sent to Jira with this add-on, the Alert Manager incident's external_reference_id is updated with the Jira Issue ID.

This add-on is based on the Splunk Add-on for Atlassian JIRA Alerts https://splunkbase.splunk.com/app/2888/

## Installation

Once the app is installed, go to the app management page in the Splunk
interface. Click `Set up` in the Jira Ticket Creation row. Fill out the required
attributes for your JIRA installation and you are ready to go.

### Usage
Within Alert Manager, you can use it as an external workflow action.

```| sendalert alert_manager-jira param.summary="My Header" param.description="My Description Body" param.priority="Highest" param.assignee="<username>"```

For Jira Service Desk you can use:

```| sendalert alert_manager-jira param.summary="My Summary" param.description="My Description" param.request_participants="<email1>[,<email2>]+" param.organization_names="<customer1>[,<customer2>]+" param.customfield_10200="<customfieldvalue>" param.requesttype_id="<requesttype_id>" param.incident_id="$incident_id$"```

The workflow action will update the external_reference_id and also add a comment.

## License
The Splunk Add-on for Atlassian JIRA Alerts is licensed under the Apache License 2.0. Details can be found in the [LICENSE page](http://www.apache.org/licenses/LICENSE-2.0).

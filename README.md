# Alert Manager JIRA Add-on

## Introduction

This add-on allows Splunk to create JIRA issues from Alert Manager https://splunkbase.splunk.com/app/2665/

When an Alert Manager Incident is sent to JIRA with this add-on, the Alert Manager incident's external_reference_id is updated with the JIRA Issue ID.

This add-on is based on the Splunk Add-on for Atlassian JIRA Alerts https://splunkbase.splunk.com/app/2888/

## Installation

Once the app is installed, go to the app management page in the Splunk
interface. Click `Set up` in the JIRA Ticket Creation row. Fill out the required
attributes for your JIRA installation and you are ready to go.

### Usage
Within Alert Manager, you can use it as an external workflow action.

```| sendalert alert_manager-jira param.summary="My Header" param.description="My Description Body" param.priority="Highest" param.assignee="<username>"```

The workflow action will update the external_reference_id and also add a comment.

## License
The Splunk Add-on for Atlassian JIRA Alerts is licensed under the Apache License 2.0. Details can be found in the [LICENSE page](http://www.apache.org/licenses/LICENSE-2.0).
